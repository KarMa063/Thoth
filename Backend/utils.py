import re
from typing import List
from langdetect import detect as ld_detect

# LANGUAGE DETECTION
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

# UTILS
def normalize_ws(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()

def clean_output(t: str) -> str:
    if not t:
        return ""
    t = t.strip().replace('"""', '').replace("'''", "")
    t = re.sub(r"#+\s*", "", t)
    t = re.sub(r"\*{2,}", "", t)
    t = re.sub(r"'\s*##\s*", "", t)
    t = t.replace("\ufffd", "")
    t = re.sub(r"^\s*(rewritten|rewrite|original|text|style|constraints).{0,80}:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.strip().strip('"').strip("'").strip()
    t = re.sub(r"([a-zA-Z])([A-Z])", r"\1 \2", t)
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)  
    t = re.sub(r"([.,!?;:])([a-zA-Z])", r"\1 \2", t)

    t = re.sub(r"(?i)(\n|\s)+(Note|Explanation|Translation|Meaning|Analysis):\s+.*$", "", t, flags=re.DOTALL)
    if re.fullmatch(r'["\'\.\s]+', t):
        return ""
    return t

def is_degenerate(t: str) -> bool:
    """Detect repetitive / degenerate output (same phrase repeated many times)."""
    words = t.lower().split()
    if len(words) < 10:
        return False
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

# Regex: keep only ASCII + Devanagari (U+0900-U+097F) + common punctuation
_ALLOWED_NE_RE = re.compile(r"[^\u0000-\u007F\u0900-\u097F]")

def strip_non_devanagari(t: str) -> str:
    """Remove any non-Devanagari Indic scripts (Gujarati, Bengali, etc.) from text.
    Keeps ASCII + Devanagari only — exactly what Nepali needs."""
    t = _ALLOWED_NE_RE.sub("", t)
    # Collapse leftover whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t

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
