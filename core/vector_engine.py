import math
import re
from typing import Dict, List, Tuple, Any, Optional


import zlib


class VectorSearchEngine:
    """
    Lightweight Semantic Vector Engine.
    Generates dense embeddings via continuous bag-of-words / n-gram projections
    and performs fast cosine similarity indexing across documents and sentences.
    """

    def __init__(self, vector_dim: int = 128):
        self.vector_dim = vector_dim
        self.index: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _hash_token(token: str, dim: int) -> Tuple[int, float]:
        """Maps a token to a consistent vector dimension and directional sign."""
        h = zlib.crc32(token.encode("utf-8"))
        idx = h % dim
        sign = 1.0 if (h % 2 == 0) else -1.0
        return idx, sign

    def encode(self, text: str) -> List[float]:
        """
        Encodes a string into a dense unit-normalized semantic vector of length vector_dim.
        """
        words = re.sub(r"[^\w\s]", " ", text.lower()).split()
        if not words:
            return [0.0] * self.vector_dim

        vec = [0.0] * self.vector_dim

        # 1-gram & 2-gram feature projection
        for i, w in enumerate(words):
            idx1, sign1 = self._hash_token(w, self.vector_dim)
            vec[idx1] += sign1 * 1.0

            if i < len(words) - 1:
                bigram = f"{w}_{words[i+1]}"
                idx2, sign2 = self._hash_token(bigram, self.vector_dim)
                vec[idx2] += sign2 * 1.5

        # L2 Unit Normalization
        norm = math.sqrt(sum(x**2 for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    @staticmethod
    def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
        """Computes cosine similarity between two normalized vectors (0.0 to 100.0)."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return round(max(0.0, min(100.0, dot * 100.0)), 2)

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Indexes a document and its sentence vectors."""
        doc_vec = self.encode(text)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n{2,}', text) if len(s.strip()) > 5]
        sentence_vecs = [{"text": s, "vec": self.encode(s)} for s in sentences]

        self.index[doc_id] = {
            "doc_vec": doc_vec,
            "sentence_vecs": sentence_vecs,
            "metadata": metadata or {},
        }

    def search_top_k(self, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Finds top-k most semantically similar documents in the index."""
        q_vec = self.encode(query_text)
        results = []

        for doc_id, data in self.index.items():
            sim = self.cosine_distance(q_vec, data["doc_vec"])
            results.append({
                "doc_id": doc_id,
                "similarity": sim,
                "metadata": data.get("metadata", {}),
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]
