import os
import re
import pickle
from typing import List, Dict, Any, Optional
from collections import Counter

import numpy as np
import torch
import faiss
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from langdetect import detect as ld_detect

# ============================================================
# CONFIG
# ============================================================

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

GEN_MODEL_EN = "google/flan-t5-base"   # English
GEN_MODEL_NE = "google/mt5-base"       # Nepali (mT5)

MODEL_DIR = "./model"
CHUNKS_PKL = os.path.join(MODEL_DIR, "chunks.pkl")
FAISS_INDEX = os.path.join(MODEL_DIR, "faiss.index")

MAX_EXEMPLARS = 8
DEVICE = "cpu"  # keep as you had

print("[author_rag] Loading EN generator …")
tokenizer_en = AutoTokenizer.from_pretrained(GEN_MODEL_EN)
generator_en = AutoModelForSeq2SeqLM.from_pretrained(GEN_MODEL_EN).to(DEVICE).eval()

print("[author_rag] Loading NE generator …")
tokenizer_ne = AutoTokenizer.from_pretrained(GEN_MODEL_NE)
generator_ne = AutoModelForSeq2SeqLM.from_pretrained(GEN_MODEL_NE).to(DEVICE).eval()

print("[author_rag] Generators ready.")

# ============================================================
# LANGUAGE DETECTION
# ============================================================

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

def detect_lang(text: str) -> str:
    # quick + robust for Nepali
    if DEVANAGARI_RE.search(text):
        return "ne"
    try:
        lang = ld_detect(text)
        # langdetect often returns hi/mr for Nepali-ish Devanagari contexts
        if lang in ("ne", "hi", "mr"):
            return "ne"
        return "en"
    except Exception:
        return "en"

# ============================================================
# STOPWORDS (anchors only)
# ============================================================

STOP_EN = set("""
the a an and or but if when while as of to for in on at by from with into
is are was were be been being it its he she they we you
that this these those who which what where why how
""".split())

STOP_NE = set("""
र मा को कि पनि अनि वा तर भने हो हुन् थियो थिए भएको भएका
यो त्यो यी ती नै मात्र धेरै सबै के कसरी कहाँ किन
""".split())

# ============================================================
# TEXT UTILITIES
# ============================================================

def normalize_ws(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()

def tokenize_words(text: str) -> List[str]:
    return re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)

def top_content_words(text: str, lang: str, k: int = 12) -> List[str]:
    toks = [t.lower() for t in tokenize_words(text)]
    if lang == "ne":
        toks = [t for t in toks if t not in STOP_NE and len(t) > 1]
    else:
        toks = [t for t in toks if t not in STOP_EN and len(t) > 2]
    return [w for w, _ in Counter(toks).most_common(k)]

def sent_split(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?\u0964\u0965]+", text) if s.strip()]

def stylometrics(text: str, lang: str) -> Dict[str, Any]:
    sents = sent_split(text)
    words = tokenize_words(text)
    T = len(words)
    types = len(set([w.lower() for w in words]))
    ttr = types / T if T else 0.0
    lens = [len(tokenize_words(s)) for s in sents] or [0]
    return {
        "ttr": round(ttr, 4),
        "avg_sent_len": round(float(np.mean(lens)), 2),
        "std_sent_len": round(float(np.std(lens)), 2),
        "anchors": top_content_words(text, lang, 12),
    }

# ============================================================
# STYLE SHEET (sentence length not necessary -> keep anchors only)
# ============================================================

def build_style_sheet(exemplars: List[Dict[str, Any]], lang: str) -> Dict[str, Any]:
    if not exemplars:
        return {"anchors": []}

    anchors = []
    for e in exemplars:
        anchors.extend(top_content_words(e["chunk"], lang, 12))

    return {
        "anchors": [w for w, _ in Counter(anchors).most_common(10)],
    }

def summarize_exemplars(exemplars: List[Dict[str, Any]]) -> str:
    out = []
    for e in exemplars[:2]:
        txt = normalize_ws(e["chunk"])[:200]
        out.append(txt)
    return "\n".join(out)


# ============================================================
# RAG RETRIEVAL
# ============================================================

def retrieve_exemplars(query: str, author: str, k: int):
    qv = embedder.encode([query], normalize_embeddings=True)
    _, ids = faiss_index.search(qv, min(k * 6, len(corpus_chunks)))

    hits = []
    for i in ids[0]:
        row = corpus_chunks[i]
        if row["author"].lower() == author.lower():
            hits.append(row)
        if len(hits) >= k:
            break

    # fallback if author filter returns nothing
    return hits if hits else corpus_chunks[:k]

# ============================================================
# PROMPTING
# - Sentence length removed
# - Added translation handling via force_lang
# ============================================================

def compose_prompt(user_text: str, style: Dict[str, Any], author: str, src_lang: str, out_lang: str, exemplar_text: str) -> str:
    anchors = style.get("anchors", [])
    anchors_str = ", ".join(anchors) if anchors else ""

    # ---- EN OUTPUT (FLAN-T5) ----
    if out_lang == "en":
        if src_lang == "ne":
            # Nepali -> English translation
            return f"""
Translate the following text into natural English.

TEXT:
{user_text}

ENGLISH:
""".strip()

        # English rewrite in author style (RAG-conditioned)
        return f"""
Rewrite the text in the literary style of {author}. Preserve meaning, but adapt tone and phrasing.
Constraints:
- Keep the same number of sentences if possible.
- Do not include labels like [Author] or any metadata.
- Keep proper punctuation.


Use these exemplar snippets as style guidance (do not copy exact sentences):
{exemplar_text}

Style anchors (use naturally if appropriate): {anchors_str}

TEXT:
{user_text}

REWRITE:
""".strip()

    # ---- NE OUTPUT (mT5) ----
    # Keep prompt short + structured; mT5 often fails with huge instructions
    if src_lang == "en":
        # English -> Nepali translation (this is your supervisor scenario)
        # mT5 understands task prefixes reasonably well
        return f"translate English to Nepali: {user_text}"

    # Nepali rewrite (RAG-conditioned but short)
    # Use: "paraphrase:" style + include tiny exemplar hint
    # (still RAG because exemplar is injected)
    prompt = (
        "paraphrase in Nepali: "
        f"{user_text}\n\n"
        f"style hints (do not copy): {exemplar_text}\n"
    )
    if anchors_str:
        prompt += f"keywords to prefer: {anchors_str}\n"
    return prompt.strip()

# ============================================================
# GENERATION (LANGUAGE-ADAPTIVE)
# - supervisor: skip_special_tokens=True (not False)
# - extra cleanup for <extra_id_*> and weird leftovers
# ============================================================

_EXTRA_ID_RE = re.compile(r"<extra_id_\d+>")
BRACKET_TAG_RE = re.compile(r"\[[^\]]{1,40}\]") 

def _clean_generated(text: str) -> str:
    text = text.strip()
    text = _EXTRA_ID_RE.sub("", text)
    text = BRACKET_TAG_RE.sub("", text)

    # Fix common OCR-ish / PDF hyphenations: "in­ human" / "in- human"
    text = re.sub(r"(\w)[\-­]\s+(\w)", r"\1\2", text)

    # Fix broken word splits like "coun try" (simple heuristic)
    text = re.sub(r"\b([a-zA-Z]{2,})\s([a-zA-Z]{2,})\b", lambda m: m.group(0), text)

    text = re.sub(r"\s+", " ", text).strip()

    # If model forgot ending punctuation, add a period (nice for demo)
    if text and text[-1] not in ".!?।":
        text += "."
    return text


def generate_text(prompt: str, out_lang: str) -> str:
    if out_lang == "ne":
        tokenizer = tokenizer_ne
        model = generator_ne
        max_len = 256

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=max_len
        ).to(model.device)

        # more verbose output
        with torch.no_grad():
            output = model.generate(
            **inputs,
            max_new_tokens=200,
            do_sample=True,
            temperature=0.85,
            top_p=0.92,
            repetition_penalty=1.1,
            no_repeat_ngram_size=3,
        )


    else:
        tokenizer = tokenizer_en
        model = generator_en
        max_len = 384

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=max_len
        ).to(model.device)

        with torch.no_grad():
            with torch.no_grad():
                output = model.generate(
                **inputs,
                max_new_tokens=220,
                do_sample=False,
                num_beams=4,
                length_penalty=1.0,
                repetition_penalty=1.12,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )

    
    # ✅ supervisor change here
    text = tokenizer.decode(output[0], skip_special_tokens=True).strip()
    return _clean_generated(text)

# ============================================================
# LOAD ARTIFACTS
# ============================================================

if not os.path.isfile(CHUNKS_PKL) or not os.path.isfile(FAISS_INDEX):
    raise RuntimeError("Model artifacts missing. Export from Colab.")

with open(CHUNKS_PKL, "rb") as f:
    corpus_chunks = pickle.load(f)

AUTHORS = sorted({c["author"] for c in corpus_chunks})

faiss_index = faiss.read_index(FAISS_INDEX)
embedder = SentenceTransformer(EMBED_MODEL, device=DEVICE)

print("[author_rag] Ready — English + Nepali supported")

# ============================================================
# PUBLIC API
# - Added force_lang parameter to support:
#   English input -> Nepali output, Nepali input -> English output
# ============================================================

def get_authors() -> List[str]:
    return AUTHORS

def rag_author_rewrite(text: str, author: str, force_lang: Optional[str] = None) -> Dict[str, Any]:
    """
    force_lang:
      - None: output language = detected language (default)
      - "en": always return English
      - "ne": always return Nepali
    """
    if author not in AUTHORS:
        raise ValueError(f"Unknown author: {author}")

    text = normalize_ws(text)
    src_lang = detect_lang(text)

    out_lang = src_lang
    if force_lang in ("en", "ne"):
        out_lang = force_lang

    exemplars = retrieve_exemplars(text, author, MAX_EXEMPLARS)
    style = build_style_sheet(exemplars, src_lang)  # anchors based on src lang
    exemplar_text = summarize_exemplars(exemplars)

    prompt = compose_prompt(
        user_text=text,
        style=style,
        author=author,
        src_lang=src_lang,
        out_lang=out_lang,
        exemplar_text=exemplar_text
    )

    rewritten = generate_text(prompt, out_lang)

    return {
        "language": out_lang,
        "detected_input_language": src_lang,
        "author": author,
        "rewritten": rewritten,
        "exemplars_used": [e.get("path", "") for e in exemplars],
        "style_sheet": style,
        "analysis": {
            "source_metrics": stylometrics(text, src_lang),
            "output_metrics": stylometrics(rewritten, out_lang),
        },
    }
