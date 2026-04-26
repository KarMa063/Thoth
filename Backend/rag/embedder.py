import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer

from config import Config

class EmbedderService:
    def __init__(self, config: Config):
        self._config = config
        self._model: SentenceTransformer = None

    def load(self) -> None:
        if self._config.debug_print:
            print("[EmbedderService] Loading embedder …")
        self._model = SentenceTransformer(self._config.embed_model, device=self._config.device)

    def encode(self, texts: List[str], normalize: bool = True, batch_size: int = 32) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("EmbedderService not loaded.")
        return self._model.encode(texts, normalize_embeddings=normalize, batch_size=batch_size)
