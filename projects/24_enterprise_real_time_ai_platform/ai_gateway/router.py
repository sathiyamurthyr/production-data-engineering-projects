"""AI Gateway Router - Multi-model routing with load balancing and fallback."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel


class ModelCapability(str, Enum):
    """Model capabilities."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE = "image"
    AUDIO = "audio"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    VISION = "vision"


class RoutingStrategy(str, Enum):
    """Routing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    CAPABILITY_BASED = "capability_based"


class ModelEndpoint(BaseModel):
    """Model endpoint configuration."""
    model_id: str
    provider: str
    endpoint: str
    api_key: str
    capabilities: list[ModelCapability]
    cost_per_1k_tokens: float
    max_tokens: int
    timeout: int
    weight: int = 1
    is_active: bool = True
    health_status: str = "healthy"
    last_health_check: datetime | None = None
    metrics: dict[str, Any] = {}


class RoutingRequest(BaseModel):
    """Routing request."""
    user_id: str
    capability: ModelCapability
    prompt_tokens: int
    max_tokens: int
    prefer_cost: bool = False
    prefer_latency: bool = False
    fallback_models: list[str] = []


class RoutingResult(BaseModel):
    """Routing result."""
    model_endpoint: ModelEndpoint
    reason: str
    estimated_cost: float
    estimated_latency: float
    fallback_available: bool


class ModelRouter:
    """Route requests to optimal LLM endpoints."""
    
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED):
        """Initialize model router.
        
        Args:
            strategy: Routing strategy
        """
        self.strategy = strategy
        self.endpoints: dict[str, ModelEndpoint] = {}
        self.request_counts: dict[str, int] = {}
        self.circuit_breakers: dict[str, dict[str, Any]] = {}
    
    def register_endpoint(self, endpoint: ModelEndpoint) -> None:
        """Register model endpoint.
        
        Args:
            endpoint: Model endpoint configuration
        """
        self.endpoints[endpoint.model_id] = endpoint
        self.request_counts[endpoint.model_id] = 0
        self.circuit_breakers[endpoint.model_id] = {
            "failures": 0,
            "last_failure": None,
            "is_open": False,
        }
    
    def route(self, request: RoutingRequest) -> RoutingResult:
        """Route request to optimal model.
        
        Args:
            request: Routing request
            
        Returns:
            Routing result with selected model
        """
        # Filter by capability
        capable_endpoints = [
            ep for ep in self.endpoints.values()
            if request.capability in ep.capabilities and ep.is_active
        ]
        
        if not capable_endpoints:
            raise ValueError(f"No endpoints available for capability: {request.capability.value}")
        
        # Filter out circuit-broken endpoints
        healthy_endpoints = [
            ep for ep in capable_endpoints
            if not self.circuit_breakers[ep.model_id]["is_open"]
        ]
        
        if not healthy_endpoints:
            # Try fallback models
            if request.fallback_models:
                fallback_endpoints = [
                    self.endpoints[model_id]
                    for model_id in request.fallback_models
                    if model_id in self.endpoints
                ]
                if fallback_endpoints:
                    return self._select_endpoint(fallback_endpoints, request, "fallback")
            
            raise ValueError("All endpoints are unavailable")
        
        # Select endpoint based on strategy
        return self._select_endpoint(healthy_endpoints, request, "normal")
    
    def _select_endpoint(
        self,
        endpoints: list[ModelEndpoint],
        request: RoutingRequest,
        mode: str,
    ) -> RoutingResult:
        """Select endpoint based on strategy.
        
        Args:
            endpoints: Available endpoints
            request: Routing request
            mode: Selection mode
            
        Returns:
            Routing result
        """
        if self.strategy == RoutingStrategy.COST_OPTIMIZED or request.prefer_cost:
            selected = min(endpoints, key=lambda ep: ep.cost_per_1k_tokens)
            reason = "cost_optimized"
        
        elif self.strategy == RoutingStrategy.LATENCY_OPTIMIZED or request.prefer_latency:
            selected = min(endpoints, key=lambda ep: ep.metrics.get("avg_latency", 1000))
            reason = "latency_optimized"
        
        elif self.strategy == RoutingStrategy.LEAST_CONNECTIONS:
            selected = min(endpoints, key=lambda ep: self.request_counts[ep.model_id])
            reason = "least_connections"
        
        elif self.strategy == RoutingStrategy.WEIGHTED:
            # Weighted random selection
            weights = [ep.weight for ep in endpoints]
            selected = np.random.choice(endpoints, p=np.array(weights) / sum(weights))
            reason = "weighted"
        
        elif self.strategy == RoutingStrategy.CAPABILITY_BASED:
            # Select based on capabilities
            selected = max(endpoints, key=lambda ep: len(ep.capabilities))
            reason = "capability_based"
        
        else:  # ROUND_ROBIN
            # Select next in round-robin
            min_count = min(self.request_counts[ep.model_id] for ep in endpoints)
            candidates = [ep for ep in endpoints if self.request_counts[ep.model_id] == min_count]
            selected = candidates[0]
            reason = "round_robin"
        
        # Update request count
        self.request_counts[selected.model_id] += 1
        
        # Calculate estimates
        estimated_cost = (request.prompt_tokens + request.max_tokens) / 1000 * selected.cost_per_1k_tokens
        estimated_latency = selected.metrics.get("avg_latency", 1000)
        
        return RoutingResult(
            model_endpoint=selected,
            reason=reason,
            estimated_cost=estimated_cost,
            estimated_latency=estimated_latency,
            fallback_available=len(endpoints) > 1,
        )
    
    def record_success(self, model_id: str, latency: float) -> None:
        """Record successful request.
        
        Args:
            model_id: Model ID
            latency: Request latency in ms
        """
        if model_id not in self.endpoints:
            return
        
        # Update metrics
        endpoint = self.endpoints[model_id]
        if "latencies" not in endpoint.metrics:
            endpoint.metrics["latencies"] = []
        endpoint.metrics["latencies"].append(latency)
        
        # Keep only last 100 latencies
        if len(endpoint.metrics["latencies"]) > 100:
            endpoint.metrics["latencies"] = endpoint.metrics["latencies"][-100:]
        
        # Update average latency
        endpoint.metrics["avg_latency"] = np.mean(endpoint.metrics["latencies"])
        
        # Update success rate
        if "success_count" not in endpoint.metrics:
            endpoint.metrics["success_count"] = 0
        endpoint.metrics["success_count"] += 1
        
        # Reset circuit breaker
        cb = self.circuit_breakers[model_id]
        if cb["is_open"]:
            cb["is_open"] = False
            cb["failures"] = 0
    
    def record_failure(self, model_id: str, error: str) -> None:
        """Record failed request.
        
        Args:
            model_id: Model ID
            error: Error message
        """
        if model_id not in self.endpoints:
            return
        
        # Update failure count
        endpoint = self.endpoints[model_id]
        if "failure_count" not in endpoint.metrics:
            endpoint.metrics["failure_count"] = 0
        endpoint.metrics["failure_count"] += 1
        
        # Update circuit breaker
        cb = self.circuit_breakers[model_id]
        cb["failures"] += 1
        cb["last_failure"] = datetime.now()
        
        # Open circuit breaker if too many failures
        if cb["failures"] >= 5:
            cb["is_open"] = True
            endpoint.health_status = "unhealthy"


class LoadBalancer:
    """Load balancer for distributing requests."""
    
    def __init__(self):
        """Initialize load balancer."""
        self.endpoints: list[ModelEndpoint] = []
        self.current_index = 0
    
    def add_endpoint(self, endpoint: ModelEndpoint) -> None:
        """Add endpoint to load balancer.
        
        Args:
            endpoint: Model endpoint
        """
        self.endpoints.append(endpoint)
    
    def round_robin(self) -> ModelEndpoint:
        """Round-robin selection.
        
        Returns:
            Selected endpoint
        """
        if not self.endpoints:
            raise ValueError("No endpoints available")
        
        endpoint = self.endpoints[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.endpoints)
        
        return endpoint
    
    def least_connections(self, request_counts: dict[str, int]) -> ModelEndpoint:
        """Least connections selection.
        
        Args:
            request_counts: Current request counts per endpoint
            
        Returns:
            Selected endpoint
        """
        if not self.endpoints:
            raise ValueError("No endpoints available")
        
        return min(self.endpoints, key=lambda ep: request_counts.get(ep.model_id, 0))
    
    def weighted_random(self) -> ModelEndpoint:
        """Weighted random selection.
        
        Returns:
            Selected endpoint
        """
        if not self.endpoints:
            raise ValueError("No endpoints available")
        
        weights = [ep.weight for ep in self.endpoints]
        return np.random.choice(self.endpoints, p=np.array(weights) / sum(weights))


class CacheManager:
    """Cache manager for AI responses."""
    
    def __init__(self, redis_client, ttl: int = 3600):
        """Initialize cache manager.
        
        Args:
            redis_client: Redis client
            ttl: Cache TTL in seconds
        """
        self.redis = redis_client
        self.ttl = ttl
    
    def get(self, key: str) -> str | None:
        """Get cached response.
        
        Args:
            key: Cache key
            
        Returns:
            Cached response or None
        """
        return self.redis.get(key)
    
    def set(self, key: str, value: str) -> None:
        """Set cached response.
        
        Args:
            key: Cache key
            value: Response value
        """
        self.redis.setex(key, self.ttl, value)
    
    def generate_key(self, model_id: str, prompt: str, params: dict[str, Any]) -> str:
        """Generate cache key.
        
        Args:
            model_id: Model ID
            prompt: Prompt text
            params: Model parameters
            
        Returns:
            Cache key
        """
        import hashlib
        content = f"{model_id}:{prompt}:{str(sorted(params.items()))}"
        return hashlib.sha256(content.encode()).hexdigest()


class RateLimiter:
    """Rate limiter for AI requests."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.limits: dict[str, dict[str, Any]] = {}
    
    def configure(self, key: str, max_requests: int, window_seconds: int) -> None:
        """Configure rate limit.
        
        Args:
            key: Rate limit key (user_id, model_id, etc.)
            max_requests: Maximum requests
            window_seconds: Time window in seconds
        """
        self.limits[key] = {
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "requests": [],
        }
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed.
        
        Args:
            key: Rate limit key
            
        Returns:
            True if allowed
        """
        if key not in self.limits:
            return True
        
        limit = self.limits[key]
        now = datetime.now()
        
        # Remove old requests
        cutoff = now - timedelta(seconds=limit["window_seconds"])
        limit["requests"] = [ts for ts in limit["requests"] if ts > cutoff]
        
        # Check limit
        if len(limit["requests"]) >= limit["max_requests"]:
            return False
        
        # Add request
        limit["requests"].append(now)
        return True
    
    def get_reset_time(self, key: str) -> datetime | None:
        """Get time when rate limit resets.
        
        Args:
            key: Rate limit key
            
        Returns:
            Reset time or None
        """
        if key not in self.limits:
            return None
        
        limit = self.limits[key]
        if not limit["requests"]:
            return None
        
        oldest = min(limit["requests"])
        return oldest + timedelta(seconds=limit["window_seconds"])


from datetime import timedelta