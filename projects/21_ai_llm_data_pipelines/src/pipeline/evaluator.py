"""Retrieval evaluation metrics (Recall@K, MRR, nDCG@K) for RAG pipelines."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Dict, List, Sequence

from src.embeddings.embedder import BaseEmbedder
from src.vector_store.sqlite_vector_store import BaseVectorStore


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated retrieval benchmark metrics across golden queries."""

    total_queries: int
    top_k: int
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    per_query: List[Dict[str, object]]


class RAGEvaluator:
    """Evaluates vector/hybrid retrieval quality against a golden Q&A benchmark."""

    def __init__(self, embedder: BaseEmbedder, vector_store: BaseVectorStore) -> None:
        self.embedder = embedder
        self.vector_store = vector_store

    def evaluate_file(
        self,
        golden_set_path: str | Path,
        top_k: int = 3,
        mode: str = "hybrid_rrf",
    ) -> EvaluationSummary:
        cases = json.loads(Path(golden_set_path).read_text(encoding="utf-8"))
        return self.evaluate_cases(cases, top_k=top_k, mode=mode)

    def evaluate_cases(
        self,
        cases: Sequence[Dict[str, object]],
        top_k: int = 3,
        mode: str = "hybrid_rrf",
    ) -> EvaluationSummary:
        if not cases:
            return EvaluationSummary(0, top_k, 0.0, 0.0, 0.0, [])

        recalls: List[float] = []
        mrrs: List[float] = []
        ndcgs: List[float] = []
        per_query: List[Dict[str, object]] = []

        for case in cases:
            query = str(case["query"])
            expected = set(case.get("expected_doc_ids", []))
            acl_groups = case.get("acl_groups")
            query_vec = self.embedder.embed_query(query)
            results = self.vector_store.search(
                query_text=query,
                query_vector=query_vec,
                top_k=top_k,
                acl_groups=acl_groups,
                mode=mode,
            )
            retrieved_docs = self._dedupe_preserve_order([r.doc_id for r in results])

            hits = len(expected & set(retrieved_docs))
            recall = hits / len(expected) if expected else 0.0
            rr = self._reciprocal_rank(retrieved_docs, expected)
            ndcg = self._ndcg(retrieved_docs, expected, top_k)

            recalls.append(recall)
            mrrs.append(rr)
            ndcgs.append(ndcg)
            per_query.append(
                {
                    "query_id": case.get("query_id", ""),
                    "expected_doc_ids": sorted(expected),
                    "retrieved_doc_ids": retrieved_docs,
                    "recall_at_k": round(recall, 4),
                    "reciprocal_rank": round(rr, 4),
                    "ndcg_at_k": round(ndcg, 4),
                }
            )

        n = len(cases)
        return EvaluationSummary(
            total_queries=n,
            top_k=top_k,
            recall_at_k=round(sum(recalls) / n, 4),
            mrr=round(sum(mrrs) / n, 4),
            ndcg_at_k=round(sum(ndcgs) / n, 4),
            per_query=per_query,
        )

    @staticmethod
    def _dedupe_preserve_order(items: Sequence[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    @staticmethod
    def _reciprocal_rank(retrieved_docs: Sequence[str], expected: set) -> float:
        for rank, doc_id in enumerate(retrieved_docs, start=1):
            if doc_id in expected:
                return 1.0 / rank
        return 0.0

    @staticmethod
    def _ndcg(retrieved_docs: Sequence[str], expected: set, k: int) -> float:
        dcg = 0.0
        for rank, doc_id in enumerate(retrieved_docs[:k], start=1):
            if doc_id in expected:
                dcg += 1.0 / math.log2(rank + 1)
        ideal_hits = min(len(expected), k)
        idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
        return dcg / idcg if idcg > 0 else 0.0
