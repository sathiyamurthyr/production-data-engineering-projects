"""Conversation Memory - Manage conversation history and context."""

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Conversation message."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = {}


class ConversationMemory:
    """Manage conversation history."""
    
    def __init__(self, max_messages: int = 100):
        """Initialize conversation memory.
        
        Args:
            max_messages: Maximum messages to store
        """
        self.max_messages = max_messages
        self.messages: list[Message] = []
    
    def add_message(self, role: str, content: str, metadata: dict[str, Any] = None) -> Message:
        """Add message to conversation.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata
            
        Returns:
            Created message
        """
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )
        
        self.messages.append(message)
        
        # Trim old messages if exceeding max
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        return message
    
    def get_history(self, last_n: int = None) -> list[dict[str, str]]:
        """Get conversation history.
        
        Args:
            last_n: Get last N messages (optional)
            
        Returns:
            List of messages
        """
        messages = self.messages[-last_n:] if last_n else self.messages
        return [{"role": m.role, "content": m.content} for m in messages]
    
    def get_context(self, max_tokens: int = 4000) -> str:
        """Get conversation context within token limit.
        
        Args:
            max_tokens: Maximum tokens
            
        Returns:
            Context string
        """
        context_parts = []
        total_tokens = 0
        
        # Add messages from most recent
        for message in reversed(self.messages):
            message_tokens = len(message.content.split())
            
            if total_tokens + message_tokens > max_tokens:
                break
            
            context_parts.insert(0, f"{message.role}: {message.content}")
            total_tokens += message_tokens
        
        return "\n".join(context_parts)
    
    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []
        logger.info("Conversation memory cleared")


class VectorMemory:
    """Vector-based long-term memory."""
    
    def __init__(self, vector_store: Any, embedding_service: Any):
        """Initialize vector memory.
        
        Args:
            vector_store: Vector store
            embedding_service: Embedding service
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    async def store(self, content: str, metadata: dict[str, Any]) -> str:
        """Store memory in vector store.
        
        Args:
            content: Memory content
            metadata: Memory metadata
            
        Returns:
            Memory ID
        """
        # Generate embedding
        embedding = await self.embedding_service.embed_query(content)
        
        # Store in vector store
        memory_id = self.vector_store.add(
            vector=embedding,
            content=content,
            metadata=metadata,
        )
        
        logger.info(f"Stored memory: {memory_id}")
        return memory_id
    
    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search memories.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Search results
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_query(query)
        
        # Search vector store
        results = self.vector_store.search(
            vector=query_embedding,
            top_k=top_k,
        )
        
        return results


class SummaryMemory:
    """Summarized conversation memory."""
    
    def __init__(self, llm_service: Any, max_summary_length: int = 500):
        """Initialize summary memory.
        
        Args:
            llm_service: LLM service
            max_summary_length: Maximum summary length
        """
        self.llm_service = llm_service
        self.max_summary_length = max_summary_length
        self.summary = ""
        self.messages: list[Message] = []
    
    def add_message(self, role: str, content: str) -> None:
        """Add message and update summary.
        
        Args:
            role: Message role
            content: Message content
        """
        self.messages.append(Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
        ))
        
        # Update summary
        self._update_summary()
    
    def _update_summary(self) -> None:
        """Update conversation summary."""
        if not self.messages:
            return
        
        # Create summary prompt
        conversation = "\n".join([
            f"{m.role}: {m.content}" for m in self.messages
        ])
        
        prompt = f"""Summarize the following conversation in {self.max_summary_length} characters or less:

{conversation}

Summary:"""
        
        # Generate summary
        self.summary = self.llm_service.generate(prompt)
    
    def get_summary(self) -> str:
        """Get conversation summary.
        
        Returns:
            Summary string
        """
        return self.summary
    
    def get_recent_messages(self, last_n: int = 10) -> list[dict[str, str]]:
        """Get recent messages.
        
        Args:
            last_n: Number of messages
            
        Returns:
            List of messages
        """
        recent = self.messages[-last_n:]
        return [{"role": m.role, "content": m.content} for m in recent]