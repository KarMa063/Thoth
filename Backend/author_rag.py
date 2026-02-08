# author_rag.py  (FINAL UPDATED)
#
# Keeps your original English pipeline (FLAN + paraphraser) for EN output.
# Removes NLLB entirely.
# Uses ONLY MishanM (Llama 3.2 + PEFT adapter) for Nepali rewriting, but now:
#   - uses RAG exemplars + style_samples in the prompt
#   - generates multiple Nepali candidates
#   - reranks Nepali candidates (content similarity + novelty + anti-copy filters)
# Fixes:
#   - no more nllb_translate calls (was crashing)
#   - removes duplicate rerank call
#   - tokenizer fast->slow fallback to avoid "ModelWrapper" tokenizer.json crash
#   - safer terminators + pad_token_id
#   - stable under single GPU / CPU and DataParallel
#
# NOTE: On Windows, run uvicorn once WITHOUT --reload to avoid parallel-download cache corruption.
#       If tokenizer cache is corrupted, set env HF_FORCE_DOWNLOAD=1 once.

import os, re, pickle
from typing import List, Dict, Any, Optional, Tuple

# Stability on Windows + uvicorn reload
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import torch
import faiss
from peft import PeftModel
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM
from langdetect import detect as ld_detect


# =========================
# CONFIG
# =========================
DEBUG_PRINT_CANDS = True

MODEL_DIR = "./model"
CHUNKS_PKL = os.path.join(MODEL_DIR, "chunks.pkl")
FAISS_INDEX = os.path.join(MODEL_DIR, "faiss.index")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_EXEMPLARS = 8

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# English generators (unchanged)
GEN_MODEL_FLAN = "google/flan-t5-base"
GEN_MODEL_PARA = "ramsrigouthamg/t5_paraphraser"

# Nepali generator (MishanM via PEFT on Llama-3.2)
LLAMA_BASE_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
LLAMA_ADAPTER_MODEL = "MISHANM/Nepali_NLP_eng_to_nepali_Llama3.2_3B_instruction"

PROMPT_MAX_TOKENS_EN = 480
USER_TEXT_MAX_TOKENS = 220

NUM_CANDS_FLAN = 10
NUM_CANDS_PARA = 6

# Nepali generation
NE_MAX_NEW_TOKENS = 200
NUM_CANDS_NE = 3
NE_TEMPERATURE = 0.7
NE_TOP_P = 0.9
NE_REP_PENALTY = 1.10

# Rerank weights (EN pipeline)
W_CONTENT = 0.20
W_STYLE_DISCRIM = 0.45
W_NOVELTY = 0.35

SRC_BONUS = {"flan": 0.06, "para": 0.00, "llama": 0.02}

REJECT_COPY6_AT = 0.95
REJECT_JAC_AT   = 0.95

# Candidate quality
MIN_LEN_RATIO = 0.55
MAX_LEN_RATIO = 1.40
MUST_KEEP_MIN_RATIO = 0.70

MIN_STYLE_DISCRIM = -1e9


# =========================
# LANGUAGE DETECTION
# =========================
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

def detect_lang(text: str) -> str:
    if DEVANAGARI_RE.search(text):
        return "ne"
    try:
        lang = ld_detect(text)
        if lang in ("ne", "hi", "mr"):
            return "ne"
        return "en"
    except Exception:
        return "en"


# =========================
# UTILS
# =========================
def normalize_ws(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()

def truncate_to_tokens(tok, text: str, max_tokens: int) -> str:
    ids = tok.encode(text, add_special_tokens=False)
    if len(ids) <= max_tokens:
        return text
    return tok.decode(ids[:max_tokens], skip_special_tokens=True)

def clean_output(t: str) -> str:
    if not t:
        return ""
    t = t.strip().replace('"""', '').replace("'''", "")
    t = re.sub(r"^\s*(rewritten|rewrite|original|text|style|constraints).{0,80}:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.strip().strip('"').strip("'").strip()
    # Fix leading dot-space artifact
    if t.startswith(". "):
        t = t[2:].strip()
        
    # Remove common "Note:" or "Explanation:" artifacts from Llama-3.2
    # e.g. "Note: The rewritten text..." or "Explanation: I have used..."
    # Match newline or space followed by Note/Explanation until end of string
    cleaned = re.sub(r"(?i)(\n|\s)+(Note|Explanation|Translation|Meaning|Analysis):\s+.*$", "", t, flags=re.DOTALL)
    
    print(f"[DEBUG] RAW: {repr(t)} -> CLEANED: {repr(cleaned)}")
    t = cleaned

    if re.fullmatch(r'["\'\.\s]+', t):
        return ""
    return t

def dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        k = x.lower().strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out

def ngram_overlap_frac(a: str, b: str, n: int = 6) -> float:
    aw = a.lower().split()
    bw = b.lower().split()
    if len(aw) < n or len(bw) < n:
        return 0.0
    agrams = [" ".join(aw[i:i+n]) for i in range(len(aw)-n+1)]
    bset = set(" ".join(bw[i:i+n]) for i in range(len(bw)-n+1))
    hit = sum(1 for g in agrams if g in bset)
    return hit / max(1, len(agrams))

def token_jaccard(a: str, b: str) -> float:
    A = set(a.lower().split())
    B = set(b.lower().split())
    if not A or not B:
        return 0.0
    return len(A & B) / max(1, len(A | B))

def digits_set(t: str) -> set:
    return set(re.findall(r"\d+", t))

def added_digits_penalty(src: str, cand: str) -> int:
    return 1 if (digits_set(cand) - digits_set(src)) else 0

def exemplar_leak(candidate: str, exemplars: List[Dict[str, Any]], n: int = 9) -> bool:
    cand = normalize_ws(candidate).lower()
    cwords = cand.split()
    if len(cwords) < n:
        return False
    cgrams = set(" ".join(cwords[i:i+n]) for i in range(len(cwords)-n+1))
    for e in exemplars[:3]:
        w = normalize_ws(e.get("chunk", "")).lower().split()
        if len(w) < n:
            continue
        for i in range(len(w)-n+1):
            if " ".join(w[i:i+n]) in cgrams:
                return True
    return False

def is_questiony_junk(cand: str) -> bool:
    c = cand.strip().lower()
    if "what do you think" in c:
        return True
    if cand.strip().endswith("?"):
        return True
    if re.match(r"^(what|why|how)\b", c):
        return True
    return False

_CAP_TOKEN_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
_NUM_TOKEN_RE = re.compile(r"\b\d+\b")

def must_keep_tokens_en(text: str) -> List[str]:
    caps = _CAP_TOKEN_RE.findall(text)
    nums = _NUM_TOKEN_RE.findall(text)
    seen = set()
    out = []
    for tok in caps + nums:
        k = tok.lower()
        if k not in seen:
            seen.add(k)
            out.append(tok)
    return out

def must_keep_ratio_en(src: str, cand: str) -> float:
    must = must_keep_tokens_en(src)
    if not must:
        return 1.0
    c_low = cand.lower()
    hit = 0
    for m in must:
        if m.lower() in c_low:
            hit += 1
    return hit / len(must)


# =========================
# LOAD MODELS
# =========================
print("[author_rag] Loading embedder …")
embedder = SentenceTransformer(EMBED_MODEL, device=DEVICE)

print("[author_rag] Loading FLAN …")
tok_flan = AutoTokenizer.from_pretrained(GEN_MODEL_FLAN)
tok_flan.truncation_side = "right"
tok_flan.padding_side = "right"
flan = AutoModelForSeq2SeqLM.from_pretrained(GEN_MODEL_FLAN).to(DEVICE).eval()

print("[author_rag] Loading Paraphraser …")
tok_para = AutoTokenizer.from_pretrained(GEN_MODEL_PARA)
tok_para.truncation_side = "right"
tok_para.padding_side = "right"
para = AutoModelForSeq2SeqLM.from_pretrained(GEN_MODEL_PARA).to(DEVICE).eval()

print("[author_rag] Loading Llama-3.2 (MISHANM via PEFT) …")
tok_llama = None
llama_model = None

def load_tokenizer_with_fallback(primary_repo: str, fallback_repo: str):
    force_dl = os.getenv("HF_FORCE_DOWNLOAD", "0") == "1"

    # Try primary repo
    try:
        try:
            return AutoTokenizer.from_pretrained(primary_repo, use_fast=True, force_download=force_dl)
        except Exception as e_fast:
            print("[author_rag] Fast tokenizer failed for primary, trying slow…", repr(e_fast))
            return AutoTokenizer.from_pretrained(primary_repo, use_fast=False, force_download=force_dl)
    except Exception:
        # Fallback repo
        print(f"[author_rag] Tokenizer not found in adapter, loading from base {fallback_repo}")
        try:
            try:
                return AutoTokenizer.from_pretrained(fallback_repo, use_fast=True, force_download=force_dl)
            except Exception as e_fast:
                print("[author_rag] Fast tokenizer failed for base, trying slow…", repr(e_fast))
                return AutoTokenizer.from_pretrained(fallback_repo, use_fast=False, force_download=force_dl)
        except Exception as e:
            raise RuntimeError(f"Failed to load tokenizer from {primary_repo} or {fallback_repo}: {e}") from e

try:
    tok_llama = load_tokenizer_with_fallback(LLAMA_ADAPTER_MODEL, LLAMA_BASE_MODEL)
    if tok_llama.pad_token is None:
        tok_llama.pad_token = tok_llama.eos_token

    print(f"[author_rag] Loading Base Model: {LLAMA_BASE_MODEL}")
    base_model = AutoModelForCausalLM.from_pretrained(
        LLAMA_BASE_MODEL,
        torch_dtype="auto",
        trust_remote_code=True
    )

    print(f"[author_rag] Loading Adapter: {LLAMA_ADAPTER_MODEL}")
    llama_model = PeftModel.from_pretrained(base_model, LLAMA_ADAPTER_MODEL)

    # DON'T use DataParallel for autoregressive generate (slow/hang-prone).
    # If you want multi-GPU later, use accelerate/device_map.
    # (so: do nothing here)

    llama_model.to(DEVICE).eval()
    print("[author_rag] Llama device:", next((p.device for p in llama_model.parameters()), "unknown"))
    print("[author_rag] Llama 3.2 Adapter loaded successfully.")

except OSError as oe:
    print(f"[author_rag] OSError loading Llama: {oe}")
    if "gated" in str(oe).lower() or "401" in str(oe) or "403" in str(oe):
        print("[author_rag] CRITICAL: Missing access to gated base model 'meta-llama/Llama-3.2-3B-Instruct'.")
        print("[author_rag] Run `huggingface-cli login` and accept the license on Hugging Face.")
    import traceback
    traceback.print_exc()

except Exception as e:
    print(f"[author_rag] CRITICAL: Failed to load Llama PEFT model. Error: {e}")
    import traceback
    traceback.print_exc()


# =========================
# LOAD ARTIFACTS
# =========================
if not os.path.isfile(CHUNKS_PKL) or not os.path.isfile(FAISS_INDEX):
    raise RuntimeError("Missing artifacts: ./model/chunks.pkl or ./model/faiss.index")

with open(CHUNKS_PKL, "rb") as f:
    corpus_chunks = pickle.load(f)

AUTHORS = sorted({c.get("author", "") for c in corpus_chunks if c.get("author")})
faiss_index = faiss.read_index(FAISS_INDEX)

print(f"[author_rag] Loaded chunks={len(corpus_chunks)} | Authors={AUTHORS}")


# =========================
# CENTROIDS
# =========================
def build_author_centroids(sample_per_author: int = 240) -> Dict[str, np.ndarray]:
    by_author: Dict[str, List[str]] = {a: [] for a in AUTHORS}

    for row in corpus_chunks:
        a = row.get("author", "")
        if a in by_author and len(by_author[a]) < sample_per_author:
            txt = normalize_ws(row.get("chunk", ""))[:320]
            if txt:
                by_author[a].append(txt)

    centroids = {}
    for a, texts in by_author.items():
        if not texts:
            continue
        embs = embedder.encode(texts, normalize_embeddings=True)
        c = np.mean(embs, axis=0)
        c = c / (np.linalg.norm(c) + 1e-9)
        centroids[a] = c
    return centroids

print("[author_rag] Building author centroids …")
AUTHOR_CENTROIDS = build_author_centroids()
print("[author_rag] Centroids ready:", list(AUTHOR_CENTROIDS.keys()))


def get_authors() -> List[str]:
    return AUTHORS


# =========================
# RETRIEVAL
# =========================
def retrieve_exemplars(query: str, author: str, k: int):
    qv = embedder.encode([query], normalize_embeddings=True)
    _, ids = faiss_index.search(qv, min(k * 10, len(corpus_chunks)))

    hits = []
    al = author.lower().strip()
    for i in ids[0]:
        row = corpus_chunks[int(i)]
        if row.get("author", "").lower().strip() == al:
            hits.append(row)
        if len(hits) >= k:
            break

    if not hits:
        for row in corpus_chunks:
            if row.get("author", "").lower().strip() == al:
                hits.append(row)
            if len(hits) >= k:
                break

    return hits


# =========================
# STYLE SAMPLES
# =========================
def style_samples(exemplars: List[Dict[str, Any]], max_lines: int = 3) -> str:
    lines = []
    for e in exemplars[: max_lines * 2]:
        txt = normalize_ws(e.get("chunk", ""))
        if not txt:
            continue
        first = re.split(r"(?<=[.!?])\s+|[।]", txt)[0].strip()
        if len(first.split()) >= 6:
            lines.append(first[:180])
        if len(lines) >= max_lines:
            break
    return "\n".join(f"- {x}" for x in lines)


# =========================
# EN PROMPTS + GENERATION (unchanged)
# =========================
def compose_prompt_flan(user_text: str, author: str, style_lines: str) -> str:
    return (
        f"You are rewriting text to resemble {author}'s writing style.\n"
        f"Completely rephrase the input. Do NOT start with the same words.\n"
        f"Preserve meaning but change sentence structure drastically.\n"
        f"Do not invent new facts, names, numbers, or dates.\n\n"
        f"Style samples:\n{style_lines}\n\n"
        f"Text:\n{user_text}\n\n"
        f"Rewrite:"
    )

def compose_prompt_para(user_text: str) -> str:
    return f"paraphrase: {user_text}"

def gen_flan_candidates(prompt: str, n: int) -> List[str]:
    inp = tok_flan(prompt, return_tensors="pt", truncation=True, max_length=PROMPT_MAX_TOKENS_EN).to(flan.device)
    with torch.no_grad():
        outs = flan.generate(
            **inp,
            max_new_tokens=260,
            do_sample=True,
            temperature=1.0,
            top_p=0.90,
            repetition_penalty=1.18,
            no_repeat_ngram_size=4,
            num_return_sequences=n,
        )
    cands = [clean_output(tok_flan.decode(o, skip_special_tokens=True)) for o in outs]
    return [c for c in dedupe_keep_order(cands) if c]

def gen_para_candidates(user_text: str, n: int) -> List[str]:
    prompt = compose_prompt_para(user_text)
    inp = tok_para(prompt, return_tensors="pt", truncation=True, max_length=256).to(para.device)
    with torch.no_grad():
        outs = para.generate(
            **inp,
            max_new_tokens=220,
            do_sample=True,
            temperature=0.9,
            top_p=0.9,
            repetition_penalty=1.12,
            no_repeat_ngram_size=3,
            num_return_sequences=n,
        )
    cands = [clean_output(tok_para.decode(o, skip_special_tokens=True)) for o in outs]
    return [c for c in dedupe_keep_order(cands) if c]


# =========================
# STYLE DISCRIMINATIVE SCORE (EN rerank)
# =========================
def style_scores_discriminative(author: str, cand_emb: np.ndarray) -> Tuple[float, float, float]:
    tgt = AUTHOR_CENTROIDS.get(author)
    if tgt is None:
        return (0.0, 0.0, 0.0)

    style_t = float(np.dot(tgt, cand_emb))

    best_other = -1e9
    for a2, c2 in AUTHOR_CENTROIDS.items():
        if a2 == author:
            continue
        s2 = float(np.dot(c2, cand_emb))
        if s2 > best_other:
            best_other = s2

    style_discrim = style_t - best_other
    return style_t, best_other, style_discrim


def rerank(user_text: str,
           candidates: List[Dict[str, str]],
           exemplars: List[Dict[str, Any]],
           author: str) -> Tuple[str, List[Dict[str, Any]]]:

    if not candidates:
        return "", []

    u = normalize_ws(user_text)
    L = len(u)

    u_emb = embedder.encode([u], normalize_embeddings=True)[0]
    texts = [c["text"] for c in candidates]
    c_embs = embedder.encode(texts, normalize_embeddings=True)

    scored_rows = []
    best_text, best_score = "", -1e9

    for cand, emb in zip(candidates, c_embs):
        t = cand["text"]
        src = cand["src"]

        if not t:
            continue
        if is_questiony_junk(t):
            continue

        if len(t) < int(L * MIN_LEN_RATIO) or len(t) > int(L * MAX_LEN_RATIO):
            continue

        if exemplar_leak(t, exemplars, 9):
            continue
        if added_digits_penalty(u, t):
            continue

        keep = must_keep_ratio_en(u, t)
        if keep < MUST_KEEP_MIN_RATIO:
            continue

        copy6 = ngram_overlap_frac(u, t, 6)
        jac = token_jaccard(u, t)
        if copy6 >= REJECT_COPY6_AT or jac >= REJECT_JAC_AT:
            continue

        style_t, style_other, style_discrim = style_scores_discriminative(author, emb)
        if style_discrim < MIN_STYLE_DISCRIM:
            continue

        content = float(np.dot(u_emb, emb))
        novelty = 1.0 - max(copy6, jac)

        score = (
            W_CONTENT * content
            + W_STYLE_DISCRIM * style_discrim
            + W_NOVELTY * novelty
            + SRC_BONUS.get(src, 0.0)
        )

        row = {
            "text": t, "src": src,
            "copy6": copy6, "jac": jac, "keep": keep,
            "style_t": style_t, "style_other": style_other,
            "style_discrim": style_discrim,
            "score": score,
        }
        scored_rows.append(row)

        if score > best_score:
            best_score = score
            best_text = t

    return best_text, scored_rows


# =========================
# NEPALI (MISHANM) GENERATION + RERANK
# =========================
def _safe_terminators(tok) -> List[int]:
    terms = []
    if tok.eos_token_id is not None:
        terms.append(tok.eos_token_id)
    try:
        eot = tok.convert_tokens_to_ids("<|eot_id|>")
        if isinstance(eot, int) and eot >= 0 and (tok.unk_token_id is None or eot != tok.unk_token_id):
            terms.append(eot)
    except Exception:
        pass
    # unique
    out = []
    seen = set()
    for x in terms:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def gen_ne_candidates(text: str, author: str, exemplars: List[Dict[str, Any]], n: int) -> List[str]:
    if llama_model is None or tok_llama is None:
        return []

    styles = style_samples(exemplars, max_lines=3)
    user_trim = truncate_to_tokens(tok_llama, text, USER_TEXT_MAX_TOKENS)

    sys_msg = (
        "You are a careful writing assistant. "
        "You MUST respond fully in Nepali (Devanagari). "
        "Do NOT provide any English explanations, notes, or translations. "
        "Output ONLY the Nepali rewrite."
    )
    user_msg = (
        f"Rewrite the text in the style of {author}.\n"
        f"Hard constraints:\n"
        f"- Preserve meaning.\n"
        f"- Do NOT add new facts, names, numbers, or dates.\n"
        f"- Do NOT copy the style samples verbatim.\n"
        f"- Change phrasing and sentence structure noticeably.\n\n"
        f"Style samples:\n{styles}\n\n"
        f"Text:\n{user_trim}\n\n"
        f"Rewrite (Nepali only):"
    )

    formatted_prompt = f"<|system|>{sys_msg}<|user|>{user_msg}<|assistant|>"

    inputs = tok_llama(
        formatted_prompt,
        return_tensors="pt",
        truncation=True,
        max_length=900,
        padding=False
    ).to(DEVICE)

    inp_len = inputs.input_ids.shape[-1]
    terminators = _safe_terminators(tok_llama)

    model_to_run = llama_model.module if hasattr(llama_model, "module") else llama_model

    with torch.inference_mode():
        outputs = model_to_run.generate(
        **inputs,
        max_new_tokens=NE_MAX_NEW_TOKENS,
        do_sample=True,
        temperature=NE_TEMPERATURE,
        top_p=NE_TOP_P,
        repetition_penalty=NE_REP_PENALTY,
        no_repeat_ngram_size=3,
        num_return_sequences=n,
        eos_token_id=terminators if terminators else tok_llama.eos_token_id,
        pad_token_id=tok_llama.eos_token_id,
        )


    cands = []
    for seq in outputs:
        resp_ids = seq[inp_len:]
        resp = clean_output(tok_llama.decode(resp_ids, skip_special_tokens=True))
        if resp:
            cands.append(resp)

    return dedupe_keep_order(cands)

def rewrite_nepali(text: str, author: str) -> str:
    text = normalize_ws(text)
    if not text:
        return ""

    exemplars = retrieve_exemplars(text, author, MAX_EXEMPLARS)
    cands = gen_ne_candidates(text, author, exemplars, NUM_CANDS_NE)

    if not cands:
        return text + " [Llama model not loaded]"

    # Rerank Nepali candidates by content similarity + novelty + anti-copy filters
    u = text
    u_emb = embedder.encode([u], normalize_embeddings=True)[0]
    c_embs = embedder.encode(cands, normalize_embeddings=True)

    best_text = cands[0]
    best_score = -1e9

    for t, emb in zip(cands, c_embs):
        if is_questiony_junk(t):
            continue

        if exemplar_leak(t, exemplars, 9):
            continue
        if added_digits_penalty(u, t):
            continue

        if len(t) < int(len(u) * MIN_LEN_RATIO) or len(t) > int(len(u) * MAX_LEN_RATIO):
            continue

        copy6 = ngram_overlap_frac(u, t, 6)
        jac = token_jaccard(u, t)
        if copy6 >= REJECT_COPY6_AT or jac >= REJECT_JAC_AT:
            continue

        keep = must_keep_ratio_en(u, t)  # still preserves digits
        if keep < MUST_KEEP_MIN_RATIO:
            continue

        content = float(np.dot(u_emb, emb))
        novelty = 1.0 - max(copy6, jac)
        score = 0.75 * content + 0.25 * novelty

        if score > best_score:
            best_score = score
            best_text = t

    if DEBUG_PRINT_CANDS:
        print(f"\n[NE-CANDS] author={author} count={len(cands)}")
        for i, t in enumerate(cands, 1):
            print(f"  {i}. {t}")
        print(f"[NE-CHOSEN] {best_text}\n")

    return best_text


# =========================
# PUBLIC API
# =========================
def rag_author_rewrite(text: str, author: str, force_lang: Optional[str] = None) -> Dict[str, Any]:
    if author not in AUTHORS:
        raise ValueError(f"Unknown author: {author}")

    text = normalize_ws(text)
    src_lang = detect_lang(text)
    out_lang = force_lang if force_lang in ("en", "ne") else src_lang

    def rewrite_english(english_text: str) -> Dict[str, Any]:
        exemplars = retrieve_exemplars(english_text, author, MAX_EXEMPLARS)
        styles = style_samples(exemplars, max_lines=3)

        user_trim = truncate_to_tokens(tok_flan, english_text, USER_TEXT_MAX_TOKENS)

        cands: List[Dict[str, str]] = []

        for t in gen_para_candidates(user_trim, NUM_CANDS_PARA):
            cands.append({"text": t, "src": "para"})

        prompt = compose_prompt_flan(user_trim, author, styles)
        for t in gen_flan_candidates(prompt, NUM_CANDS_FLAN):
            cands.append({"text": t, "src": "flan"})

        deduped = []
        seen = set()
        for c in cands:
            k = c["text"].lower().strip()
            if not k or k in seen:
                continue
            seen.add(k)
            deduped.append(c)

        chosen, scored = rerank(user_trim, deduped, exemplars, author)

        if not chosen:
            flans = [c["text"] for c in deduped if c["src"] == "flan"]
            pool = flans if flans else [c["text"] for c in deduped]
            if pool:
                u_emb = embedder.encode([user_trim], normalize_embeddings=True)[0]
                e = embedder.encode(pool, normalize_embeddings=True)
                idx = int(np.argmax([float(np.dot(u_emb, ee)) for ee in e]))
                chosen = pool[idx]
            else:
                chosen = user_trim

        if DEBUG_PRINT_CANDS:
            print(f"\n[CANDS-EN] author={author} count={len(deduped)}")
            for i, c in enumerate(deduped, 1):
                t = c["text"]
                src = c["src"]
                copy6 = ngram_overlap_frac(user_trim, t, 6)
                jac = token_jaccard(user_trim, t)
                keep = must_keep_ratio_en(user_trim, t)
                nd = added_digits_penalty(user_trim, t)
                emb = embedder.encode([t], normalize_embeddings=True)[0]
                st, so, sd = style_scores_discriminative(author, emb)
                print(f"  {i}. src={src:4s} (copy6={copy6:.3f} jac={jac:.3f} keep={keep:.3f} sd={sd:.3f} newDigits={nd}) {t}")
            print(f"[CHOSEN-EN] {chosen}\n")

            if scored:
                top = sorted(scored, key=lambda r: r["score"], reverse=True)[:5]
                print("[TOP-SCORES-EN]")
                for r in top:
                    print(f"  score={r['score']:.3f} sd={r['style_discrim']:.3f} src={r['src']} copy6={r['copy6']:.3f} jac={r['jac']:.3f} -> {r['text'][:120]}...")

        return {"rewritten": chosen, "exemplars": exemplars}

    # OUTPUT EN (NLLB removed)
    if out_lang == "en":
        pack = rewrite_english(text)
        return {
            "language": "en",
            "detected_input_language": src_lang,
            "author": author,
            "rewritten": pack["rewritten"],
            "exemplars_used": [e.get("path", "") for e in pack["exemplars"]],
        }

    # OUTPUT NE (MishanM only)
    if out_lang == "ne":
        rewritten_ne = rewrite_nepali(text, author)
        return {
            "language": "ne",
            "detected_input_language": src_lang,
            "author": author,
            "rewritten": rewritten_ne,
            "exemplars_used": [],
        }

    return rag_author_rewrite(text, author, force_lang="en")
