import os
import pickle
from typing import List, Dict, Any
import faiss

from config import Config

class ArtifactStore:
    def __init__(self, config: Config):
        self._config = config
        self._chunks: List[Dict[str, Any]] = []
        self._index: faiss.Index = None

    def load(self) -> None:
        chunks_pkl = os.path.join(self._config.model_dir, "chunks.pkl")
        faiss_index_path = os.path.join(self._config.model_dir, "faiss.index")

        if not os.path.isfile(chunks_pkl) or not os.path.isfile(faiss_index_path):
            raise RuntimeError(f"Missing artifacts: {chunks_pkl} or {faiss_index_path}")

        with open(chunks_pkl, "rb") as f:
            self._chunks = pickle.load(f)

        self._index = faiss.read_index(faiss_index_path)

        if self._config.debug_print:
            print(f"[ArtifactStore] Loaded chunks={len(self._chunks)}")

    @property
    def chunks(self) -> List[Dict[str, Any]]:
        return self._chunks

    @property
    def faiss_index(self) -> faiss.Index:
        return self._index
