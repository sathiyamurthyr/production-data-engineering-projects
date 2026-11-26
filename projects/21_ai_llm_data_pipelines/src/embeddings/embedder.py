"""Embedding generation strategies with batching, retries, and cost estimation."""

from abc import ABC, abstractmethod
import hashlib
import json
import math
import os
import re
import time
from typing import Callable, List, Optional, Sequence
import urllib.error
import urllib.request

from src.models import EmbeddedChunk, TextChunk


def estimate_embedding_cost_usd(total_tokens: int, cost_per_1m_tokens_usd: float = 0.02) -> float:
    """Estimate embedding API spend in USD."""
    return round((total_tokens / 1_000_000) * cost_per_1m_tokens_usd, 8)


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, model_name: str, dimensions: int, batch_size: int = 16) -> None:
        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = batch_size

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        """Generate normalized embedding vectors for a batch of texts."""

    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query."""
        return self.embed_texts([query])[0]

    def embed_chunks(self, chunks: Sequence[TextChunk]) -> List[EmbeddedChunk]:
        """Batch-embed TextChunks into EmbeddedChunks."""
        if not chunks:
            return []
        embedded: List[EmbeddedChunk] = []
        for start in range(0, len(chunks), self.batch_size):
            batch = chunks[start : start + self.batch_size]
            vectors = self.embed_texts([c.text for c in batch])
            for chunk, vector in zip(batch, vectors):
                embedded.append(
                    EmbeddedChunk(chunk=chunk, embedding=vector, model_name=self.model_name)
                )
        return embedded


class DeterministicHashEmbedder(BaseEmbedder):
    """
    Offline deterministic feature-hashing embedder over word unigrams and bigrams.
    Produces L2-normalized vectors ideal for local testing and CI pipelines.
    """

    TOKEN_RE = re.compile(r"[a-z0-9_]+")

    def __init__(
        self,
        model_name: str = "local-hash-v1",
        dimensions: int = 128,
        batch_size: int = 16,
    ) -> None:
        super().__init__(model_name=model_name, dimensions=dimensions, batch_size=batch_size)

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        return [self._embed_single(text) for text in texts]

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self.dimensions
        tokens = self.TOKEN_RE.findall(text.lower())
        if not tokens:
            return vec

        features = list(tokens) + [
            f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1)
        ]
        for feat in features:
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            raw_int = int.from_bytes(digest, "little")
            idx = raw_int % self.dimensions
            sign = 1.0 if ((raw_int >> 1) & 1) == 0 else -1.0
            weight = 1.5 if "_" in feat else 1.0
            vec[idx] += sign * weight

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [round(v / norm, 6) for v in vec]
        return vec


class OpenAICompatibleEmbedder(BaseEmbedder):
    """
    Production adapter for OpenAI-compatible /v1/embeddings endpoints
    with exponential backoff retry and injectable HTTP transport for testing.
    """

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        dimensions: int = 1536,
        batch_size: int = 64,
        max_retries: int = 3,
        api_base: str = "https://api.openai.com/v1",
        api_key_env: str = "OPENAI_API_KEY",
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(model_name=model_name, dimensions=dimensions, batch_size=batch_size)
        self.max_retries = max_retries
        self.api_base = api_base.rstrip("/")
        self.api_key_env = api_key_env
        self._sleep = sleep_fn

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key environment variable: {self.api_key_env}")

        payload = json.dumps({"model": self.model_name, "input": list(texts)}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            req = urllib.request.Request(
                f"{self.api_base}/embeddings", data=payload, headers=headers, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    sorted_items = sorted(body["data"], key=lambda item: item["index"])
                    return [item["embedding"] for item in sorted_items]
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    self._sleep(0.5 * (2**attempt))

        raise RuntimeError(f"Embedding API failed after {self.max_retries} attempts: {last_error}")
