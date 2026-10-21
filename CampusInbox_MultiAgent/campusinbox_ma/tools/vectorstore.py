"""A tiny vector store (stdlib only) for retrieval over the imported mails.

Each mail sentence is stored as a sparse TF-IDF-style vector (a dict of
term -> weight). Retrieval is cosine similarity between the query vector and
the stored vectors. This is a real vector database in miniature - same idea as
FAISS/Chroma (embed text, store vectors, nearest-neighbour search) but small
enough to read in one sitting and with no dependencies.
"""
from __future__ import annotations

import math
import re
from collections import Counter

STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "to", "of",
    "and", "or", "in", "on", "for", "by", "at", "with", "this", "that",
    "it", "its", "as", "from", "will", "be", "all", "dear", "regards",
    "hello", "students", "your", "you", "we", "our",
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 1]


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    n = max(1, len(tokens))
    return {t: (c / n) * idf.get(t, 0.0) for t, c in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(w * b.get(t, 0.0) for t, w in a.items())
    na = math.sqrt(sum(w * w for w in a.values()))
    nb = math.sqrt(sum(w * w for w in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class VectorStore:
    """Stores sentence vectors and answers nearest-neighbour queries."""

    def __init__(self):
        self._docs: list[dict] = []   # {text, source, vector}
        self._idf: dict[str, float] = {}

    @staticmethod
    def sentences(text: str) -> list[str]:
        chunks = []
        for line in text.splitlines():
            chunks.extend(re.split(r"(?<=[.!?])\s+", line))
        return [c.strip() for c in chunks if len(c.strip()) > 15]

    def add_mail(self, subject: str, body: str) -> int:
        """Embed one mail's sentences and store their vectors."""
        added = 0
        for s in self.sentences(body):
            self._docs.append({"text": s, "source": subject, "tokens": _tokens(s)})
            added += 1
        self._rebuild()
        return added

    def _rebuild(self) -> None:
        df = Counter()
        for d in self._docs:
            df.update(set(d["tokens"]))
        n = max(1, len(self._docs))
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        for d in self._docs:
            d["vector"] = _vector(d["tokens"], self._idf)

    def search(self, query: str, k: int = 3, min_score: float = 0.05) -> list[dict]:
        """Return the k nearest sentences to the query, with source and score."""
        qv = _vector(_tokens(query), self._idf)
        scored = [(_cosine(qv, d["vector"]), d) for d in self._docs]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"text": d["text"], "source": d["source"], "score": round(s, 3)}
                for s, d in scored[:k] if s >= min_score]

    def __len__(self) -> int:
        return len(self._docs)
