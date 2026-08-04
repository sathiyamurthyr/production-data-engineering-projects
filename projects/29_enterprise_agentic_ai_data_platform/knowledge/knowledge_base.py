"""
Knowledge Base for Enterprise Agentic AI Platform

This module provides the enterprise knowledge base for agents.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import uuid
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KnowledgeDocument(BaseModel):
    """Knowledge document"""
    doc_id: str
    title: str
    content: str
    category: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class KnowledgeBase:
    """
    Enterprise knowledge base
    
    This service provides:
    - Document storage
    - Semantic retrieval
    - Knowledge categorization
    - Search capabilities
    """
    
    def __init__(self, config: Dict):
        """Initialize knowledge base"""
        self.config = config
        self.documents: Dict[str, KnowledgeDocument] = {}
        logger.info("Knowledge Base initialized")
    
    async def add_document(self, title: str, content: str, category: str,
                           tags: Optional[List[str]] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> KnowledgeDocument:
        """Add a knowledge document"""
        doc_id = f"doc-{uuid.uuid4().hex[:12]}"
        
        doc = KnowledgeDocument(
            doc_id=doc_id,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.documents[doc_id] = doc
        return doc
    
    async def search(self, query: str, category: Optional[str] = None,
                     limit: int = 10) -> List[KnowledgeDocument]:
        """Search documents by keyword"""
        query_lower = query.lower()
        
        results = []
        for doc in self.documents.values():
            if category and doc.category != category:
                continue
            
            score = 0.0
            if query_lower in doc.title.lower():
                score += 1.0
            if query_lower in doc.content.lower():
                score += 0.6
            
            for tag in doc.tags:
                if tag.lower() in query_lower:
                    score += 0.4
            
            for word in query_lower.split():
                if word in doc.content.lower():
                    score += 0.1
            
            if score > 0:
                results.append((score, doc))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in results[:limit]]
    
    async def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Get document by ID"""
        return self.documents.get(doc_id)
    
    async def get_by_category(self, category: str) -> List[KnowledgeDocument]:
        """Get documents by category"""
        return [d for d in self.documents.values() if d.category == category]
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get knowledge base analytics"""
        total = len(self.documents)
        
        by_category = {}
        for doc in self.documents.values():
            cat = doc.category
            by_category[cat] = by_category.get(cat, 0) + 1
        
        return {
            "total_documents": total,
            "by_category": by_category
        }