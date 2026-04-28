import numpy as np
from typing import List, Dict, Tuple, Any

from config import Config
from rag import EmbedderService, AuthorRegistry
from utils import (
    normalize_ws, clean_output, is_questiony_junk, added_digits_penalty,
    ngram_overlap_frac, token_jaccard, must_keep_ratio_en, is_degenerate
)

class Reranker:
    def __init__(self, config: Config, embedder: EmbedderService, registry: AuthorRegistry):
        self._config = config
        self._embedder = embedder
        self._registry = registry

    def rerank(self, user_text: str, candidates: List[str], exemplars: List[Dict[str, Any]], author: str) -> Tuple[str, List[Dict[str, Any]]]:
        if not candidates:
            return "", []

        u = normalize_ws(user_text)
        L = len(u)

        u_emb = self._embedder.encode([u], normalize=True)[0]
        c_embs = self._embedder.encode(candidates, normalize=True)

        scored = []
        best_text, best_score = "", -1e9

        for t, emb in zip(candidates, c_embs):
            if not t:
                continue
            if is_questiony_junk(t):
                continue
            if len(t) < int(L * self._config.min_len_ratio) or len(t) > int(L * self._config.max_len_ratio):
                continue
            if added_digits_penalty(u, t):
                continue

            copy6 = ngram_overlap_frac(u, t, 6)
            jac = token_jaccard(u, t)
            if copy6 >= self._config.reject_copy6_at or jac >= self._config.reject_jac_at:
                continue

            keep = must_keep_ratio_en(u, t)
            if keep < 0.35:
                continue

            style_t, style_other, style_discrim = self._registry.style_scores_discriminative(author, emb)
            content = float(np.dot(u_emb, emb))
            novelty = 1.0 - max(copy6, jac)

            score = self._config.w_content * content + self._config.w_style_discrim * style_discrim + self._config.w_novelty * novelty
            row = {
                "text": t,
                "score": score,
                "copy6": copy6,
                "jac": jac,
                "keep": keep,
                "style_discrim": style_discrim,
                "content": content,
                "novelty": novelty,
            }
            scored.append(row)

            if score > best_score:
                best_score = score
                best_text = t

        if not best_text and candidates:
            for fallback in candidates:
                fallback = clean_output(fallback)
                if not fallback or is_questiony_junk(fallback) or is_degenerate(fallback):
                    continue
                if self._config.debug_print:
                    print(f"[Reranker] All candidates filtered; using cleaned fallback.")
                return fallback, scored

        return best_text, scored
