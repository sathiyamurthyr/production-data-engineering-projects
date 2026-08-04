"""
Enterprise Memory for Agentic AI Platform

This module provides persistent memory for agents across sessions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import uuid
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MemoryEntry(BaseModel):
    """Memory entry"""
    memory_id: str
    agent_id: str
    session_id: str
    memory_type: str  # fact, preference, learning, context
    content: str
    importance: float  # 0.0 - 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: Optional[datetime] = None


class EnterpriseMemory:
    """
    Enterprise memory system
    
    This service provides:
    - Persistent agent memory
    - Memory retrieval
    - Memory importance scoring
    - Memory lifecycle management
    """
    
    def __init__(self, config: Dict):
        """Initialize enterprise memory"""
        self.config = config
        self.memories: Dict[str, MemoryEntry] = {}
        self.retention_days = config.get("retention_days", 90)
        logger.info("Enterprise Memory initialized")
    
    async def store(self, agent_id: str, session_id: str, memory_type: str,
                    content: str, importance: float = 0.5,
                    metadata: Optional[Dict[str, Any]] = None,
                    ttl_days: Optional[int] = None) -> MemoryEntry:
        """Store a memory"""
        memory_id = f"mem-{uuid.uuid4().hex[:12]}"
        
        expires_at = None
        if ttl_days:
            expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        
        entry = MemoryEntry(
            memory_id=memory_id,
            agent_id=agent_id,
            session_id=session_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )
        
        self.memories[memory_id] = entry
        await self._cleanup_expired()
        return entry
    
    async def retrieve(self, agent_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       memory_type: Optional[str] = None,
                       min_importance: float = 0.0,
                       limit: int = 50) -> List[MemoryEntry]:
        """Retrieve memories"""
        results = list(self.memories.values())
        
        if agent_id:
            results = [m for m in results if m.agent_id == agent_id]
        if session_id:
            results = [m for m in results if m.session_id == session_id]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if min_importance:
            results = [m for m in results if m.importance >= min_importance]
        
        # Sort by importance then recency
        results.sort(key=lambda m: (m.importance, m.created_at), reverse=True)
        
        # Filter expired
        results = [m for m in results if not m.expires_at or m.expires_at > datetime.utcnow()]
        
        return results[:limit]
    
    async def recall(self, agent_id: str, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Simple recall by keyword matching"""
        results = [m for m in self.memories.values() if m.agent_id == agent_id]
        query_lower = query.lower()
        
        scored = []
        for memory in results:
            score = 0.0
            if query_lower in memory.content.lower():
                score += 0.5
            for word in query_lower.split():
                if word in memory.content.lower():
                    score += 0.1
            
            # Combine with importance
            total = score * 0.7 + memory.importance * 0.3
            if score > 0:
                scored.append((total, memory))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]
    
    async def forget(self, memory_id: str) -> bool:
        """Delete a memory"""
        if memory_id in self.memories:
            del self.memories[memory_id]
            return True
        return False
    
    async def _cleanup_expired(self) -> None:
        """Remove expired memories"""
        now = datetime.utcnow()
        cutoff = now - timedelta(days=self.retention_days)
        
        expired_ids = [
            mid for mid, mem in self.memories.items()
            if mem.created_at < cutoff or (mem.expires_at and mem.expires_at < now)
        ]
        
        for mid in expired_ids:
            del self.memories[mid]
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get memory analytics"""
        total = len(self.memories)
        
        by_type = {}
        by_agent = {}
        for memory in self.memories.values():
            mtype = memory.memory_type
            by_type[mtype] = by_type.get(mtype, 0) + 1
            by_agent[memory.agent_id] = by_agent.get(memory.agent_id, 0) + 1
        
        avg_importance = sum(m.importance for m in self.memories.values()) / total if total > 0 else 0
        
        return {
            "total_memories": total,
            "avg_importance": avg_importance,
            "by_type": by_type,
            "by_agent": by_agent
        }