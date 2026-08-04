"""Embedding Service - Generate and manage embeddings for documents."""

import logging
from datetime import datetime
from typing import Any

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EmbeddingModel(BaseModel):
    """Embedding model configuration."""
    model_id: str
    provider: str
    model_name: str
    dimension: int
    max_tokens: int
    cost_per_1k_tokens: float


class EmbeddingRequest(BaseModel):
    """Embedding request."""
    texts: list[str]
    model_id: str | None = None
    metadata: dict[str, Any] = {}


class EmbeddingResponse(BaseModel):
    """Embedding response."""
    embeddings: list[list[float]]
    model_id: str
    token_count: int
    latency_ms: float


class EmbeddingService:
    """Service for generating embeddings."""
    
    def __init__(self, default_model: str = "openai-text-embedding-3-large"):
        """Initialize embedding service.
        
        Args:
            default_model: Default embedding model
        """
        self.default_model = default_model
        self.models: dict[str, EmbeddingModel] = {}
        self._register_default_models()
    
    def _register_default_models(self) -> None:
        """Register default embedding models."""
        self.models["openai-text-embedding-3-large"] = EmbeddingModel(
            model_id="openai-text-embedding-3-large",
            provider="openai",
            model_name="text-embedding-3-large",
            dimension=3072,
            max_tokens=8191,
            cost_per_1k_tokens=0.00013,
        )
        self.models["openai-text-embedding-3-small"] = EmbeddingModel(
            model_id="openai-text-embedding-3-small",
            provider="openai",
            model_name="text-embedding-3-small",
            dimension=1536,
            max_tokens=8191,
            cost_per_1k_tokens=0.00002,
        )
        self.models["azure-ada-002"] = EmbeddingModel(
            model_id="azure-ada-002",
            provider="azure",
            model_name="text-embedding-ada-002",
            dimension=1536,
            max_tokens=8191,
            cost_per_1k_tokens=0.0001,
        )
        self.models["cohere-embed-v3"] = EmbeddingModel(
            model_id="cohere-embed-v3",
            provider="cohere",
            model_name="embed-english-v3.0",
            dimension=1024,
            max_tokens=512,
            cost_per_1k_tokens=0.0001,
        )
    
    def register_model(self, model: EmbeddingModel) -> None:
        """Register custom embedding model.
        
        Args:
            model: Embedding model configuration
        """
        self.models[model.model_id] = model
    
    async def embed_documents(self, texts: list[str], model_id: str = None) -> EmbeddingResponse:
        """Generate embeddings for documents.
        
        Args:
            texts: List of texts to embed
            model_id: Model ID (optional)
            
        Returns:
            Embedding response
        """
        model_id = model_id or self.default_model
        
        if model_id not in self.models:
            raise ValueError(f"Unknown model: {model_id}")
        
        model = self.models[model_id]
        start_time = datetime.now()
        
        try:
            # Generate embeddings based on provider
            if model.provider == "openai":
                embeddings = await self._embed_openai(texts, model)
            elif model.provider == "azure":
                embeddings = await self._embed_azure(texts, model)
            elif model.provider == "cohere":
                embeddings = await self._embed_cohere(texts, model)
            else:
                raise ValueError(f"Unsupported provider: {model.provider}")
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            token_count = sum(len(t.split()) for t in texts)
            
            logger.info(f"Generated {len(embeddings)} embeddings using {model_id}")
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model_id=model_id,
                token_count=token_count,
                latency_ms=latency_ms,
            )
        
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def embed_query(self, query: str, model_id: str = None) -> list[float]:
        """Generate embedding for a single query.
        
        Args:
            query: Query text
            model_id: Model ID (optional)
            
        Returns:
            Query embedding
        """
        response = await self.embed_documents([query], model_id)
        return response.embeddings[0]
    
    async def _embed_openai(self, texts: list[str], model: EmbeddingModel) -> list[list[float]]:
        """Generate embeddings using OpenAI.
        
        Args:
            texts: List of texts
            model: Model configuration
            
        Returns:
            List of embeddings
        """
        try:
            import openai
            
            client = openai.AsyncOpenAI()
            
            response = await client.embeddings.create(
                input=texts,
                model=model.model_name,
            )
            
            return [item.embedding for item in response.data]
        
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise
    
    async def _embed_azure(self, texts: list[str], model: EmbeddingModel) -> list[list[float]]:
        """Generate embeddings using Azure OpenAI.
        
        Args:
            texts: List of texts
            model: Model configuration
            
        Returns:
            List of embeddings
        """
        try:
            from openai import AsyncAzureOpenAI
            
            client = AsyncAzureOpenAI()
            
            response = await client.embeddings.create(
                input=texts,
                model=model.model_name,
            )
            
            return [item.embedding for item in response.data]
        
        except Exception as e:
            logger.error(f"Azure embedding failed: {e}")
            raise
    
    async def _embed_cohere(self, texts: list[str], model: EmbeddingModel) -> list[list[float]]:
        """Generate embeddings using Cohere.
        
        Args:
            texts: List of texts
            model: Model configuration
            
        Returns:
            List of embeddings
        """
        try:
            import cohere
            
            client = cohere.AsyncClient()
            
            response = await client.embed(
                texts=texts,
                model=model.model_name,
                input_type="search_document",
            )
            
            return response.embeddings
        
        except Exception as e:
            logger.error(f"Cohere embedding failed: {e}")
            raise
    
    def get_model(self, model_id: str) -> EmbeddingModel | None:
        """Get embedding model configuration.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model configuration or None
        """
        return self.models.get(model_id)
    
    def list_models(self) -> list[EmbeddingModel]:
        """List all registered models.
        
        Returns:
            List of model configurations
        """
        return list(self.models.values())


class EmbeddingVersionManager:
    """Manage embedding model versions."""
    
    def __init__(self):
        """Initialize version manager."""
        self.versions: dict[str, list[dict[str, Any]]] = {}
    
    def register_version(
        self,
        model_id: str,
        version: str,
        configuration: dict[str, Any],
    ) -> None:
        """Register embedding model version.
        
        Args:
            model_id: Model ID
            version: Version string
            configuration: Model configuration
        """
        if model_id not in self.versions:
            self.versions[model_id] = []
        
        self.versions[model_id].append({
            "version": version,
            "configuration": configuration,
            "created_at": datetime.now(),
            "is_active": True,
        })
    
    def get_version(self, model_id: str, version: str = None) -> dict[str, Any] | None:
        """Get specific version of model.
        
        Args:
            model_id: Model ID
            version: Version string (optional)
            
        Returns:
            Model version or None
        """
        if model_id not in self.versions:
            return None
        
        versions = self.versions[model_id]
        
        if version:
            for v in versions:
                if v["version"] == version:
                    return v
            return None
        else:
            # Get latest active version
            active_versions = [v for v in versions if v.get("is_active")]
            if active_versions:
                return active_versions[-1]
            return None
    
    def deactivate_version(self, model_id: str, version: str) -> bool:
        """Deactivate a model version.
        
        Args:
            model_id: Model ID
            version: Version string
            
        Returns:
            True if successful
        """
        if model_id not in self.versions:
            return False
        
        for v in self.versions[model_id]:
            if v["version"] == version:
                v["is_active"] = False
                return True
        
        return False


class EmbeddingCache:
    """Cache embeddings for reuse."""
    
    def __init__(self, redis_client=None, ttl: int = 86400):
        """Initialize embedding cache.
        
        Args:
            redis_client: Redis client
            ttl: Cache TTL in seconds (default: 24 hours)
        """
        self.redis = redis_client
        self.ttl = ttl
        self.local_cache: dict[str, list[float]] = {}
    
    def get(self, key: str) -> list[float] | None:
        """Get cached embedding.
        
        Args:
            key: Cache key
            
        Returns:
            Cached embedding or None
        """
        # Try local cache first
        if key in self.local_cache:
            return self.local_cache[key]
        
        # Try Redis cache
        if self.redis:
            cached = self.redis.get(key)
            if cached:
                import json
                embedding = json.loads(cached)
                self.local_cache[key] = embedding
                return embedding
        
        return None
    
    def set(self, key: str, embedding: list[float]) -> None:
        """Cache embedding.
        
        Args:
            key: Cache key
            embedding: Embedding vector
        """
        # Store in local cache
        self.local_cache[key] = embedding
        
        # Store in Redis if available
        if self.redis:
            import json
            self.redis.setex(key, self.ttl, json.dumps(embedding))
    
    def generate_key(self, text: str, model_id: str) -> str:
        """Generate cache key.
        
        Args:
            text: Text content
            model_id: Model ID
            
        Returns:
            Cache key
        """
        import hashlib
        content = f"{model_id}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()