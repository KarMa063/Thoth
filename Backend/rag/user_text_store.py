import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from config import Config
from utils import normalize_ws


CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WORD_RE = re.compile(r"[\w\u0900-\u097F]+", re.UNICODE)


def clean_uploaded_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = CONTROL_CHARS_RE.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


class UserTextStore:
    def __init__(self, config: Config):
        self._db_path = Path(config.database_path)

    def init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS author_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source_filename TEXT,
                    word_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "source_filename", "TEXT")
            self._ensure_column(conn, "word_count", "INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_author_samples_author
                ON author_samples(author)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS author_sample_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    author TEXT NOT NULL,
                    chunk TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    embedding_model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(sample_id) REFERENCES author_samples(id) ON DELETE CASCADE,
                    UNIQUE(sample_id, chunk_index)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_author_sample_chunks_author
                ON author_sample_chunks(author)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS base_corpus_chunks (
                    id INTEGER PRIMARY KEY,
                    author TEXT NOT NULL,
                    chunk TEXT NOT NULL,
                    source_path TEXT,
                    embedding BLOB NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    embedding_model TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_base_corpus_chunks_author
                ON base_corpus_chunks(author)
                """
            )

    def database_revision(self) -> tuple:
        with self._connect() as conn:
            sample_row = conn.execute(
                "SELECT COUNT(*) AS count, COALESCE(MAX(id), 0) AS max_id FROM author_samples"
            ).fetchone()
            chunk_row = conn.execute(
                "SELECT COUNT(*) AS count, COALESCE(MAX(id), 0) AS max_id FROM author_sample_chunks"
            ).fetchone()
        return (
            sample_row["count"],
            sample_row["max_id"],
            chunk_row["count"],
            chunk_row["max_id"],
        )

    def seed_base_corpus_embeddings(
        self,
        chunks,
        faiss_index,
        embedding_model: str,
        embedder=None,
        batch_size: int = 64,
    ) -> None:
        with self._connect() as conn:
            existing_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM base_corpus_chunks
                WHERE embedding_model = ?
                """,
                (embedding_model,),
            ).fetchone()["count"]

            if existing_count == len(chunks):
                return

            conn.execute("DELETE FROM base_corpus_chunks WHERE embedding_model = ?", (embedding_model,))
            rows = []
            missing_embedding_items = []
            for idx, chunk in enumerate(chunks):
                embedding = self._base_embedding_for_index(faiss_index, idx)
                if embedding is None:
                    missing_embedding_items.append((idx, chunk))
                    continue
                rows.append(
                    (
                        idx,
                        chunk.get("author", ""),
                        chunk.get("chunk", ""),
                        chunk.get("path", ""),
                        self._embedding_to_blob(embedding),
                        int(np.asarray(embedding).shape[0]),
                        embedding_model,
                    )
                )

            if missing_embedding_items and embedder is not None:
                for start in range(0, len(missing_embedding_items), batch_size):
                    batch = missing_embedding_items[start:start + batch_size]
                    texts = [normalize_ws(chunk.get("chunk", "")) for _, chunk in batch]
                    embeddings = embedder.encode(texts, normalize=True, batch_size=batch_size)
                    for (idx, chunk), embedding in zip(batch, embeddings):
                        rows.append(
                            (
                                idx,
                                chunk.get("author", ""),
                                chunk.get("chunk", ""),
                                chunk.get("path", ""),
                                self._embedding_to_blob(embedding),
                                int(np.asarray(embedding).shape[0]),
                                embedding_model,
                            )
                        )

            conn.executemany(
                """
                INSERT INTO base_corpus_chunks(
                    id,
                    author,
                    chunk,
                    source_path,
                    embedding,
                    embedding_dim,
                    embedding_model
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def add_sample(
        self,
        author: str,
        text: str,
        source_filename: str = "",
        embedder=None,
        embedding_model: str = "",
    ) -> List[Dict[str, Any]]:
        author = normalize_ws(author)
        text = clean_uploaded_text(text)
        word_count = count_words(text)
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO author_samples(author, text, source_filename, word_count, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (author, text, source_filename, word_count, now),
            )
            sample_id = cur.lastrowid

        chunks = self._sample_to_chunks(sample_id, author, text, now)
        if embedder is not None:
            self._save_chunk_embeddings(sample_id, chunks, embedder, embedding_model)
            return self._chunk_rows_from_db(sample_id=sample_id)
        return chunks

    def backfill_embeddings(self, embedder, embedding_model: str) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, author, text, created_at
                FROM author_samples
                ORDER BY id ASC
                """
            ).fetchall()

            ready_sample_ids = {
                row["sample_id"]
                for row in conn.execute(
                    """
                    SELECT sample_id
                    FROM author_sample_chunks
                    WHERE embedding_model = ?
                    GROUP BY sample_id
                    """,
                    (embedding_model,),
                ).fetchall()
            }

        for row in rows:
            if row["id"] in ready_sample_ids:
                continue
            chunks = self._sample_to_chunks(row["id"], row["author"], row["text"], row["created_at"])
            self._save_chunk_embeddings(row["id"], chunks, embedder, embedding_model)

    def list_chunks(self) -> List[Dict[str, Any]]:
        return self._chunk_rows_from_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(author_samples)")}
        if column not in columns:
            conn.execute(f"ALTER TABLE author_samples ADD COLUMN {column} {definition}")

    def _save_chunk_embeddings(
        self,
        sample_id: int,
        chunks: List[Dict[str, Any]],
        embedder,
        embedding_model: str,
    ) -> None:
        if not chunks:
            return

        texts = [row["chunk"] for row in chunks]
        embeddings = embedder.encode(texts, normalize=True, batch_size=64)

        with self._connect() as conn:
            conn.execute("DELETE FROM author_sample_chunks WHERE sample_id = ?", (sample_id,))
            conn.executemany(
                """
                INSERT INTO author_sample_chunks(
                    sample_id,
                    chunk_index,
                    author,
                    chunk,
                    embedding,
                    embedding_dim,
                    embedding_model,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sample_id,
                        idx,
                        chunk["author"],
                        chunk["chunk"],
                        self._embedding_to_blob(embedding),
                        int(np.asarray(embedding).shape[0]),
                        embedding_model,
                        chunk["created_at"],
                    )
                    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1)
                ],
            )

    def _chunk_rows_from_db(self, sample_id: int = None) -> List[Dict[str, Any]]:
        sql = """
            SELECT
                c.sample_id,
                c.chunk_index,
                c.author,
                c.chunk,
                c.embedding,
                c.embedding_dim,
                c.embedding_model,
                c.created_at
            FROM author_sample_chunks c
            INNER JOIN author_samples s ON s.id = c.sample_id
        """
        params = []
        if sample_id is not None:
            sql += " WHERE c.sample_id = ?"
            params.append(sample_id)
        sql += " ORDER BY c.sample_id ASC, c.chunk_index ASC"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "author": row["author"],
                "chunk": row["chunk"],
                "path": f"user-db:{row['sample_id']}:{row['chunk_index']}",
                "source": "user_database",
                "created_at": row["created_at"],
                "embedding": self._blob_to_embedding(row["embedding"]),
                "embedding_dim": row["embedding_dim"],
                "embedding_model": row["embedding_model"],
            }
            for row in rows
        ]

    def _embedding_to_blob(self, embedding: np.ndarray) -> bytes:
        return np.asarray(embedding, dtype=np.float32).tobytes()

    def _blob_to_embedding(self, blob: bytes) -> np.ndarray:
        return np.frombuffer(blob, dtype=np.float32).copy()

    def _base_embedding_for_index(self, faiss_index, idx: int):
        try:
            return faiss_index.reconstruct(idx)
        except Exception:
            return None

    def _sample_to_chunks(
        self,
        sample_id: int,
        author: str,
        text: str,
        created_at: str,
        max_chars: int = 900,
    ) -> List[Dict[str, Any]]:
        parts = [
            normalize_ws(part)
            for part in re.split(r"\n{2,}|(?<=[.!?])\s+", text)
            if normalize_ws(part)
        ]
        if not parts:
            parts = [text]

        chunks = []
        buffer = ""
        chunk_num = 1
        for part in parts:
            candidate = f"{buffer} {part}".strip() if buffer else part
            if len(candidate) <= max_chars:
                buffer = candidate
                continue
            if buffer:
                chunks.append(self._chunk_row(sample_id, chunk_num, author, buffer, created_at))
                chunk_num += 1
            buffer = part[:max_chars]

        if buffer:
            chunks.append(self._chunk_row(sample_id, chunk_num, author, buffer, created_at))

        return chunks

    def _chunk_row(
        self,
        sample_id: int,
        chunk_num: int,
        author: str,
        chunk: str,
        created_at: str,
    ) -> Dict[str, Any]:
        return {
            "author": author,
            "chunk": chunk,
            "path": f"user-db:{sample_id}:{chunk_num}",
            "source": "user_database",
            "created_at": created_at,
        }
