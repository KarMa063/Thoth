import numpy as np
from typing import List, Dict, Tuple

from config import Config
from utils import normalize_ws, detect_lang
from .artifact_store import ArtifactStore
from .embedder import EmbedderService

class AuthorRegistry:
    def __init__(self, config: Config, store: ArtifactStore, embedder: EmbedderService):
        self._config = config
        self._store = store
        self._embedder = embedder
        
        self._authors: List[str] = []
        self._author_lang: Dict[str, str] = {}
        self._centroids: Dict[str, np.ndarray] = {}

    def build(self) -> None:
        self._build_authors()
        self._infer_author_langs()
        self._build_centroids()

    def _build_authors(self) -> None:
        chunks = self._store.chunks
        self._authors = sorted({c.get("author", "") for c in chunks if c.get("author")})
        if self._config.debug_print:
            print(f"[AuthorRegistry] Found Authors={len(self._authors)}")

    def _infer_author_langs(self, sample_per_author: int = 80) -> None:
        counts = {a: {"ne": 0, "en": 0} for a in self._authors}
        seen = {a: 0 for a in self._authors}

        for row in self._store.chunks:
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
        self._author_lang = out

        if self._config.debug_print:
            ne_authors = sum(1 for a in self._authors if out.get(a) == "ne")
            print(f"[AuthorRegistry] Inferred author langs. Nepali authors={ne_authors}, English authors={len(self._authors)-ne_authors}")

    def _build_centroids(self, sample_per_author: int = 240, batch_size: int = 64) -> None:
        if self._config.debug_print:
            print("[AuthorRegistry] Building author centroids …")
            
        samples = []
        sample_authors = []
        count = {a: 0 for a in self._authors}

        for row in self._store.chunks:
            a = row.get("author", "")
            if a in count and count[a] < sample_per_author:
                txt = normalize_ws(row.get("chunk", ""))[:320]
                if txt:
                    samples.append(txt)
                    sample_authors.append(a)
                    count[a] += 1

        if not samples:
            return

        embs = self._embedder.encode(samples, normalize=True, batch_size=batch_size)
        by_author: Dict[str, List[np.ndarray]] = {a: [] for a in self._authors}
        for a, e in zip(sample_authors, embs):
            by_author[a].append(e)

        centroids = {}
        for a, vecs in by_author.items():
            if not vecs:
                continue
            c = np.mean(np.vstack(vecs), axis=0)
            c = c / (np.linalg.norm(c) + 1e-9)
            centroids[a] = c.astype(np.float32)
        
        self._centroids = centroids
        if self._config.debug_print:
            print("[AuthorRegistry] Centroids ready:", len(self._centroids))

    def get_authors(self) -> List[str]:
        return self._authors

    def get_lang(self, author: str) -> str:
        return self._author_lang.get(author, "en")

    def get_centroid(self, author: str) -> np.ndarray:
        return self._centroids.get(author)

    def get_all_centroids(self) -> Dict[str, np.ndarray]:
        return self._centroids

    def validate_lang_or_raise(self, text: str, author: str) -> Tuple[str, str]:
        src_lang = detect_lang(text)
        author_lang = self.get_lang(author)
        if src_lang != author_lang:
            raise ValueError(
                f"Language mismatch: selected author writes {author_lang.upper()}, "
                f"but your input is {src_lang.upper()}. "
                f"Please paste {author_lang.upper()} text or choose a {src_lang.upper()} author."
            )
        return src_lang, author_lang

    def style_scores_discriminative(self, author: str, cand_emb: np.ndarray) -> Tuple[float, float, float]:
        tgt = self.get_centroid(author)
        if tgt is None:
            return (0.0, 0.0, 0.0)

        style_t = float(np.dot(tgt, cand_emb))
        best_other = -1e9
        for a2, c2 in self._centroids.items():
            if a2 == author:
                continue
            s2 = float(np.dot(c2, cand_emb))
            if s2 > best_other:
                best_other = s2
        style_discrim = style_t - best_other
        return style_t, best_other, style_discrim
