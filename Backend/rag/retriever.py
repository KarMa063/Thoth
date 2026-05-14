import re
from typing import List, Dict, Any

from config import Config
from utils import normalize_ws
from .artifact_store import ArtifactStore
from .embedder import EmbedderService

class RetrieverService:
    def __init__(self, config: Config, store: ArtifactStore, embedder: EmbedderService):
        self._config = config
        self._store = store
        self._embedder = embedder

    def retrieve_exemplars(self, query: str, author: str, k: int) -> List[Dict[str, Any]]:
        qv = self._embedder.encode([query], normalize=True)
        
        chunks = self._store.chunks
        index = self._store.faiss_index
        
        search_k = min(k * 10, len(chunks), index.ntotal)
        _, ids = index.search(qv, search_k)

        hits = []
        al = author.lower().strip()
        for i in ids[0]:
            if i < 0:
                continue
            row = chunks[int(i)]
            if row.get("author", "").lower().strip() == al:
                hits.append(row)
            if len(hits) >= k:
                break

        if not hits:
            for row in chunks:
                if row.get("author", "").lower().strip() == al:
                    hits.append(row)
                if len(hits) >= k:
                    break
        return hits

    def style_samples(self, exemplars: List[Dict[str, Any]], max_lines: int = 3) -> str:
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
