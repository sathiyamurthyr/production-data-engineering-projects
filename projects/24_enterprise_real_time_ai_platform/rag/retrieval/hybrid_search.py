"""Hybrid Search - Combine dense and sparse retrieval with reranking."""

import logging
from typing import Any

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Search result."""
    chunk_id: str
    content: str
    metadata: dict[str, Any]
    score: float
    rerank_score: float | None = None
    source: str


class HybridSearch:
    """Hybrid search combining dense and sparse retrieval."""
    
    def __init__(
        self,
        vector_store: Any,
        sparse_retriever: Any = None,
        alpha: float = 0.5,
        top_k: int = 10,
    ):
        """Initialize hybrid search.
        
        Args:
            vector_store: Vector store for dense retrieval
            sparse_retriever: Sparse retriever (BM25)
            alpha: Weight for dense vs sparse (0=sparse, 1=dense)
            top_k: Number of results to return
        """
        self.vector_store = vector_store
        self.sparse_retriever = sparse_retriever
        self.alpha = alpha
        self.top_k = top_k
    
    def search(
        self,
        query: str,
        query_embedding: list[float] = None,
        top_k: int = None,
        filters: dict[str, Any] = None,
    ) -> list[SearchResult]:
        """Perform hybrid search.
        
        Args:
            query: Search query
            query_embedding: Query embedding (optional)
            top_k: Number of results
            filters: Metadata filters
            
        Returns:
            List of search results
        """
        top_k = top_k or self.top_k
        
        # Dense retrieval
        dense_results = self._dense_search(query_embedding, top_k * 2, filters)
        
        # Sparse retrieval
        if self.sparse_retriever:
            sparse_results = self._sparse_search(query, top_k * 2)
        else:
            sparse_results = []
        
        # Combine results
        combined = self._merge_results(dense_results, sparse_results)
        
        # Return top-k
        return combined[:top_k]
    
    def _dense_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] = None,
    ) -> list[SearchResult]:
        """Dense vector search.
        
        Args:
            query_embedding: Query embedding
            top_k: Number of results
            filters: Metadata filters
            
        Returns:
            Search results
        """
        # Query vector store
        results = self.vector_store.search(
            vector=query_embedding,
            top_k=top_k,
            filters=filters,
        )
        
        return [
            SearchResult(
                chunk_id=result["id"],
                content=result["content"],
                metadata=result.get("metadata", {}),
                score=result["score"],
                source="dense",
            )
            for result in results
        ]
    
    def _sparse_search(self, query: str, top_k: int) -> list[SearchResult]:
        """Sparse keyword search (BM25).
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Search results
        """
        if not self.sparse_retriever:
            return []
        
        results = self.sparse_retriever.search(query, top_k=top_k)
        
        return [
            SearchResult(
                chunk_id=result["id"],
                content=result["content"],
                metadata=result.get("metadata", {}),
                score=result["score"],
                source="sparse",
            )
            for result in results
        ]
    
    def _merge_results(
        self,
        dense_results: list[SearchResult],
        sparse_results: list[SearchResult],
    ) -> list[SearchResult]:
        """Merge dense and sparse results.
        
        Args:
            dense_results: Dense search results
            sparse_results: Sparse search results
            
        Returns:
            Merged results
        """
        # Normalize scores
        dense_normalized = self._normalize_scores(dense_results)
        sparse_normalized = self._normalize_scores(sparse_results)
        
        # Combine scores
        merged: dict[str, SearchResult] = {}
        
        for result in dense_normalized:
            chunk_id = result.chunk_id
            merged[chunk_id] = SearchResult(
                chunk_id=chunk_id,
                content=result.content,
                metadata=result.metadata,
                score=self.alpha * result.score,
                source="hybrid",
            )
        
        for result in sparse_normalized:
            chunk_id = result.chunk_id
            if chunk_id in merged:
                merged[chunk_id].score += (1 - self.alpha) * result.score
            else:
                merged[chunk_id] = SearchResult(
                    chunk_id=chunk_id,
                    content=result.content,
                    metadata=result.metadata,
                    score=(1 - self.alpha) * result.score,
                    source="hybrid",
                )
        
        # Sort by score
        return sorted(merged.values(), key=lambda x: x.score, reverse=True)
    
    def _normalize_scores(self, results: list[SearchResult]) -> list[SearchResult]:
        """Normalize scores to 0-1 range.
        
        Args:
            results: Search results
            
        Returns:
            Results with normalized scores
        """
        if not results:
            return []
        
        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return results
        
        score_range = max_score - min_score
        
        normalized = []
        for result in results:
            normalized_score = (result.score - min_score) / score_range
            normalized.append(
                SearchResult(
                    chunk_id=result.chunk_id,
                    content=result.content,
                    metadata=result.metadata,
                    score=normalized_score,
                    source=result.source,
                )
            )
        
        return normalized


class Reranker:
    """Rerank search results using cross-encoder."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize reranker.
        
        Args:
            model_name: Cross-encoder model name
        """
        self.model_name = model_name
        self.model = None
    
    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Rerank search results.
        
        Args:
            query: Search query
            results: Search results
            top_k: Number of results to return
            
        Returns:
            Reranked results
        """
        if not results:
            return []
        
        # Load model (lazy loading)
        if not self.model:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
        
        # Prepare pairs
        pairs = [(query, result.content) for result in results]
        
        # Score pairs
        scores = self.model.predict(pairs)
        
        # Update scores
        for result, score in zip(results, scores):
            result.rerank_score = float(score)
        
        # Sort by rerank score
        reranked = sorted(results, key=lambda x: x.rerank_score or 0, reverse=True)
        
        return reranked[:top_k]


class QueryRewriter:
    """Rewrite queries for better retrieval."""
    
    def __init__(self, llm_service: Any):
        """Initialize query rewriter.
        
        Args:
            llm_service: LLM service
        """
        self.llm_service = llm_service
    
    async def rewrite(self, query: str) -> str:
        """Rewrite query for better retrieval.
        
        Args:
            query: Original query
            
        Returns:
            Rewritten query
        """
        prompt = f"""Rewrite the following query to improve search results.
Make it more specific and detailed while preserving the original intent.

Original query: {query}

Rewritten query:"""
        
        rewritten = await self.llm_service.generate(prompt)
        return rewritten.strip()
    
    async def decompose(self, query: str) -> list[str]:
        """Decompose complex query into sub-queries.
        
        Args:
            query: Complex query
            
        Returns:
            List of sub-queries
        """
        prompt = f"""Decompose the following complex query into simpler sub-queries.
Return each sub-query on a new line.

Complex query: {query}

Sub-queries:"""
        
        response = await self.llm_service.generate(prompt)
        sub_queries = [q.strip() for q in response.strip().split("\n") if q.strip()]
        return sub_queries


class MetadataFilter:
    """Filter search results by metadata."""
    
    def __init__(self):
        """Initialize metadata filter."""
        pass
    
    def apply(self, results: list[SearchResult], filters: dict[str, Any]) -> list[SearchResult]:
        """Apply metadata filters to results.
        
        Args:
            results: Search results
            filters: Metadata filters
            
        Returns:
            Filtered results
        """
        filtered = []
        
        for result in results:
            match = True
            for key, value in filters.items():
                if key not in result.metadata:
                    match = False
                    break
                
                if isinstance(value, list):
                    if result.metadata[key] not in value:
                        match = False
                        break
                else:
                    if result.metadata[key] != value:
                        match = False
                        break
            
            if match:
                filtered.append(result)
        
        return filtered
    
    def apply_threshold(self, results: list[SearchResult], threshold: float) -> list[SearchResult]:
        """Filter results by score threshold.
        
        Args:
            results: Search results
            threshold: Minimum score
            
        Returns:
            Filtered results
        """
        return [r for r in results if r.score >= threshold]


class SearchCache:
    """Cache search results."""
    
    def __init__(self, redis_client=None, ttl: int = 3600):
        """Initialize search cache.
        
        Args:
            redis_client: Redis client
            ttl: Cache TTL in seconds
        """
        self.redis = redis_client
        self.ttl = ttl
        self.local_cache: dict[str, list[SearchResult]] = {}
    
    def get(self, key: str) -> list[SearchResult] | None:
        """Get cached results.
        
        Args:
            key: Cache key
            
        Returns:
            Cached results or None
        """
        if key in self.local_cache:
            return self.local_cache[key]
        
        if self.redis:
            cached = self.redis.get(key)
            if cached:
                import json
                results_data = json.loads(cached)
                results = [SearchResult(**r) for r in results_data]
                self.local_cache[key] = results
                return results
        
        return None
    
    def set(self, key: str, results: list[SearchResult]) -> None:
        """Cache results.
        
        Args:
            key: Cache key
            results: Search results
        """
        self.local_cache[key] = results
        
        if self.redis:
            import json
            results_data = [r.model_dump() for r in results]
            self.redis.setex(key, self.ttl, json.dumps(results_data))
    
    def generate_key(self, query: str, query_embedding: list[float], filters: dict[str, Any]) -> str:
        """Generate cache key.
        
        Args:
            query: Search query
            query_embedding: Query embedding
            filters: Metadata filters
            
        Returns:
            Cache key
        """
        import hashlib
        content = f"{query}:{str(query_embedding)}:{str(sorted(filters.items()))}"
        return hashlib.sha256(content.encode()).hexdigest()