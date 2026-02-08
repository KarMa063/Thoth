import numpy as np
import re
import math
from typing import Dict, Any, List
from langdetect import detect as detect_lang

from author_rag import embedder, AUTHOR_CENTROIDS


# ======================================================
# Helpers
# ======================================================

def split_sentences(text: str) -> List[str]:
    sents = re.split(r"[.!?।]+", text)
    return [s.strip() for s in sents if len(s.strip()) > 5]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def _softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x)
    e = np.exp(x)
    return e / (np.sum(e) + 1e-12)


# ======================================================
# Core embedding analysis
# ======================================================

def analyze_text_embeddings(text: str) -> Dict[str, Any]:
    sents = split_sentences(text)

    # Always return a stable structure
    if len(sents) < 2:
        return {
            "embedding_signals": {
                "emotional_intensity": 0.0,
                "semantic_drift": 0.0,
                "assertiveness": 0.0,
            },
            "sentence_stats": {
                "num_sentences": len(sents),
                "mean_sentence_similarity": None,
            },
            "notes": ["Text too short for sentence-level embedding analysis."],
        }

    sent_embs = embedder.encode(sents, normalize_embeddings=True)

    doc_emb = np.mean(sent_embs, axis=0)
    doc_emb /= np.linalg.norm(doc_emb) + 1e-9

    # Emotional intensity = embedding variance
    intensity = float(np.mean(np.var(sent_embs, axis=0)))

    # Semantic drift = sentence-to-sentence divergence
    drift_scores = [
        1.0 - cosine(sent_embs[i], sent_embs[i + 1])
        for i in range(len(sent_embs) - 1)
    ]
    semantic_drift = float(np.mean(drift_scores))

    # Assertiveness = distance from neutral centroid
    if AUTHOR_CENTROIDS:
        neutral = np.mean(list(AUTHOR_CENTROIDS.values()), axis=0)
        neutral /= np.linalg.norm(neutral) + 1e-9
        assertiveness = 1.0 - cosine(doc_emb, neutral)
    else:
        assertiveness = 0.0

    return {
        "embedding_signals": {
            "emotional_intensity": round(intensity, 4),
            "semantic_drift": round(semantic_drift, 4),
            "assertiveness": round(assertiveness, 4),
        },
        "sentence_stats": {
            "num_sentences": len(sents),
            "mean_sentence_similarity": round(
                float(np.mean([cosine(doc_emb, e) for e in sent_embs])), 4
            ),
        },
    }


# ======================================================
# Author benchmarking (semantic, not stylistic)
# ======================================================

def benchmark_author_alignment(text: str) -> Dict[str, Any]:
    emb = embedder.encode([text], normalize_embeddings=True)[0]

    sims = {
        a: round(float(cosine(emb, c)), 4)
        for a, c in AUTHOR_CENTROIDS.items()
    }

    closest = max(sims, key=sims.get) if sims else None

    return {
        "closest_author": closest,
        "similarities": sims,
        "deviation_from_author": (
            round(1.0 - sims[closest], 4) if closest else None
        ),
    }


# ======================================================
# Dynamic notes + limitations (NO if/else classifier)
# ======================================================

def dynamic_meta(
    text: str,
    emb_analysis: Dict[str, Any],
    author_profile: Dict[str, Any],
) -> Dict[str, List[str]]:

    notes: List[str] = []
    limitations: List[str] = []

    n_tokens = len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))
    n_sent = emb_analysis.get("sentence_stats", {}).get("num_sentences", 0) or 0

    # Smooth reliability estimate (no hard thresholds)
    reliability = (
        (1.0 / (1.0 + math.exp(-(n_tokens - 140) / 60.0)))
        * (1.0 / (1.0 + math.exp(-(n_sent - 4) / 1.8)))
    )

    notes.append(
        f"Sample size: ~{n_tokens} tokens across {n_sent} sentences "
        f"(estimated reliability ≈ {reliability:.2f})."
    )

    limitations.append(
        "Similarity scores are cosine similarities in embedding space, not probabilities."
    )
    limitations.append(
        "Signals are continuous and comparative; they are not categorical emotion labels."
    )

    if reliability < 0.55:
        limitations.append(
            "Short inputs reduce the stability of drift, intensity, and author-alignment signals."
        )

    sims = author_profile.get("similarities", {}) or {}
    if sims:
        items = sorted(sims.items(), key=lambda kv: kv[1], reverse=True)
        scores = np.array([v for _, v in items], dtype=np.float32)
        probs = _softmax(scores / 0.02)
        entropy = float(-(probs * np.log(probs + 1e-12)).sum())

        if len(items) >= 2:
            gap = float(items[0][1] - items[1][1])
            notes.append(
                f"Author alignment ambiguity: top-gap={gap:.4f}, "
                f"entropy={entropy:.2f} (higher entropy = weaker single-author dominance)."
            )
            limitations.append(
                "Closest-author should be interpreted as nearest semantic cluster when scores are close."
            )

    return {
        "notes": notes,
        "limitations": list(dict.fromkeys(limitations)),
    }


# ======================================================
# Public API
# ======================================================

def analyze_text_style(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"error": "Empty text"}

    tokens = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
    sentences = split_sentences(text)

    # HARD STOP: insufficient input
    if len(tokens) < 20 or len(sentences) < 2:
        return {
            "analysis_type": "insufficient-input",
            "message": "Text is too short for reliable stylometric or embedding-based analysis.",
            "details": {
                "token_count": len(tokens),
                "sentence_count": len(sentences),
                "minimum_required": {
                    "tokens": 20,
                    "sentences": 2,
                },
            },
        }

    try:
        lang = detect_lang(text)
    except Exception:
        lang = "unknown"

    emb_analysis = analyze_text_embeddings(text)
    author_profile = benchmark_author_alignment(text)

    # Language-aware explanation (NOT suppression)
    if lang != "en":
        author_profile["note"] = (
            "Author alignment uses cross-lingual sentence embeddings. "
            "For non-English input, similarities reflect semantic proximity "
            "rather than direct stylistic authorship."
        )

    meta = dynamic_meta(text, emb_analysis, author_profile)

    return {
        "analysis_type": "embedding-based (distributional)",
        "embedding_analysis": emb_analysis,
        "author_alignment": author_profile,
        "notes": meta["notes"],
        "limitations": meta["limitations"],
    }
