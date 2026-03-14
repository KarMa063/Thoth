"""
author_rag.py — RAG Infrastructure

Handles: artifact loading, embedder, author language detection,
centroids, retrieval, style scoring, and shared utilities.
"""

import os, re, pickle
from typing import List, Dict, Any, Optional, Tuple

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import torch
import faiss

from langdetect import detect as ld_detect
from sentence_transformers import SentenceTransformer


# =========================
# CONFIG
# =========================
DEBUG_PRINT = True
MODEL_DIR = "./model"
CHUNKS_PKL = os.path.join(MODEL_DIR, "chunks.pkl")
FAISS_INDEX = os.path.join(MODEL_DIR, "faiss.index")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

EN_GEN_MODEL = "Qwen/Qwen2.5-3B-Instruct"

# Nepali generator options:
# Option A (recommended): Use same EN model for Nepali too (if it handles Nepali reasonably),
# but enforce Nepali-only output & Nepali-only input for Nepali authors.
NE_GEN_MODEL = EN_GEN_MODEL

# Option B (your existing Llama + PEFT adapter) - ONLY if you truly need it
USE_NE_PEFt = False
LLAMA_BASE_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
LLAMA_ADAPTER_MODEL = "MISHANM/Nepali_NLP_eng_to_nepali_Llama3.2_3B_instruction"

# Retrieval / exemplars
MAX_EXEMPLARS = 8

# Generation caps (keep low for speed)
REWRITE_MAX_NEW_TOKENS = 180
CONT_MAX_NEW_TOKENS = 220

TEMPERATURE = 0.6
TOP_P = 0.90
REP_PENALTY = 1.15
NO_REPEAT_NGRAM = 4

# Candidate count (keep low for speed)
NUM_CANDS = 3  # Increase to 3 so reranker has choices

# Rerank weights
W_CONTENT = 0.30
W_STYLE_DISCRIM = 0.45
W_NOVELTY = 0.25

REJECT_COPY6_AT = 0.95
REJECT_JAC_AT   = 0.95

MIN_LEN_RATIO = 0.30
MAX_LEN_RATIO = 2.00


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

def clean_output(t: str) -> str:
    if not t:
        return ""
    t = t.strip().replace('"""', '').replace("'''", "")
    # Remove markdown headers and artifacts (## , **, etc.)
    t = re.sub(r"#+\s*", "", t)
    t = re.sub(r"\*{2,}", "", t)
    # Remove stray '## fragments
    t = re.sub(r"'\s*##\s*", "", t)
    # Remove unicode replacement characters (often seen in bad token boundary decoding)
    t = t.replace("\ufffd", "")
    # Remove common headings
    t = re.sub(r"^\s*(rewritten|rewrite|original|text|style|constraints).{0,80}:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.strip().strip('"').strip("'").strip()

    # strip trailing analyses
    t = re.sub(r"(?i)(\n|\s)+(Note|Explanation|Translation|Meaning|Analysis):\s+.*$", "", t, flags=re.DOTALL)
    if re.fullmatch(r'["\'\.\s]+', t):
        return ""
    return t

def is_degenerate(t: str) -> bool:
    """Detect repetitive / degenerate output (same phrase repeated many times)."""
    words = t.lower().split()
    if len(words) < 10:
        return False
    # Check 3-gram repetition: if any 3-gram appears 4+ times, it's degenerate
    trigrams = [" ".join(words[i:i+3]) for i in range(len(words)-2)]
    from collections import Counter
    counts = Counter(trigrams)
    most_common_count = counts.most_common(1)[0][1]
    return most_common_count >= 4

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

def is_questiony_junk(cand: str) -> bool:
    c = cand.strip().lower()
    if "what do you think" in c:
        return True
    if cand.strip().endswith("?"):
        return True
    if re.match(r"^(what|why|how)\b", c):
        return True
    return False


# =========================
# LOAD ARTIFACTS
# =========================
if not os.path.isfile(CHUNKS_PKL) or not os.path.isfile(FAISS_INDEX):
    raise RuntimeError("Missing artifacts: ./model/chunks.pkl or ./model/faiss.index")

with open(CHUNKS_PKL, "rb") as f:
    corpus_chunks = pickle.load(f)

AUTHORS = sorted({c.get("author", "") for c in corpus_chunks if c.get("author")})
faiss_index = faiss.read_index(FAISS_INDEX)

print(f"[author_rag] Loaded chunks={len(corpus_chunks)} | Authors={len(AUTHORS)}")


# =========================
# LOAD EMBEDDER
# =========================
print("[author_rag] Loading embedder …")
embedder = SentenceTransformer(EMBED_MODEL, device=DEVICE)


# =========================
# AUTHOR LANGUAGE MAP (AUTO)
# =========================
def infer_author_langs(sample_per_author: int = 80) -> Dict[str, str]:
    """
    Infer author language from their chunks:
    if chunk contains Devanagari, count as nepali.
    """
    counts = {a: {"ne": 0, "en": 0} for a in AUTHORS}
    seen = {a: 0 for a in AUTHORS}

    for row in corpus_chunks:
        a = row.get("author", "")
        if a not in counts:
            continue
        if seen[a] >= sample_per_author:
            continue
        txt = normalize_ws(row.get("chunk", ""))
        if not txt:
            continue
        lang = detect_lang(txt)
        counts[a]["ne" if lang == "ne" else "en"] += 1
        seen[a] += 1

    out = {}
    for a, c in counts.items():
        out[a] = "ne" if c["ne"] > c["en"] else "en"
    return out

AUTHOR_LANG = infer_author_langs()
if DEBUG_PRINT:
    ne_authors = sum(1 for a in AUTHORS if AUTHOR_LANG.get(a) == "ne")
    print(f"[author_rag] Inferred author langs. Nepali authors={ne_authors}, English authors={len(AUTHORS)-ne_authors}")


def validate_lang_or_raise(text: str, author: str) -> Tuple[str, str]:
    src_lang = detect_lang(text)
    author_lang = AUTHOR_LANG.get(author, "en")
    if src_lang != author_lang:
        raise ValueError(
            f"Language mismatch: selected author writes {author_lang.upper()}, "
            f"but your input is {src_lang.upper()}. "
            f"Please paste {author_lang.upper()} text or choose a {src_lang.upper()} author."
        )
    return src_lang, author_lang


# =========================
# CENTROIDS (FAST BUILD)
# =========================
def build_author_centroids_fast(sample_per_author: int = 240, batch_size: int = 64) -> Dict[str, np.ndarray]:
    samples = []
    sample_authors = []
    count = {a: 0 for a in AUTHORS}

    for row in corpus_chunks:
        a = row.get("author", "")
        if a in count and count[a] < sample_per_author:
            txt = normalize_ws(row.get("chunk", ""))[:320]
            if txt:
                samples.append(txt)
                sample_authors.append(a)
                count[a] += 1

    if not samples:
        return {}

    embs = embedder.encode(samples, normalize_embeddings=True, batch_size=batch_size)
    by_author: Dict[str, List[np.ndarray]] = {a: [] for a in AUTHORS}
    for a, e in zip(sample_authors, embs):
        by_author[a].append(e)

    centroids = {}
    for a, vecs in by_author.items():
        if not vecs:
            continue
        c = np.mean(np.vstack(vecs), axis=0)
        c = c / (np.linalg.norm(c) + 1e-9)
        centroids[a] = c.astype(np.float32)
    return centroids

print("[author_rag] Building author centroids …")
AUTHOR_CENTROIDS = build_author_centroids_fast()
print("[author_rag] Centroids ready:", len(AUTHOR_CENTROIDS))


# =========================
# RETRIEVAL + STYLE SAMPLES
# =========================
def retrieve_exemplars(query: str, author: str, k: int) -> List[Dict[str, Any]]:
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

    # fallback if none found
    if not hits:
        for row in corpus_chunks:
            if row.get("author", "").lower().strip() == al:
                hits.append(row)
            if len(hits) >= k:
                break
    return hits

def style_samples(exemplars: List[Dict[str, Any]], max_lines: int = 3) -> str:
    lines = []
    for e in exemplars[: max_lines * 3]:
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
# STYLE DISCRIM SCORE
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


# =========================
# PUBLIC API
# =========================
def get_authors() -> List[str]:
    return AUTHORS