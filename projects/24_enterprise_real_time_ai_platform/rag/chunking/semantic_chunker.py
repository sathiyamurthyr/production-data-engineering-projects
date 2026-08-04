"""Semantic Chunking - Split documents into semantically coherent chunks."""

import logging
from typing import Any

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Chunk(BaseModel):
    """Document chunk."""
    id: str
    content: str
    metadata: dict[str, Any]
    source_id: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int


class SemanticChunker:
    """Semantic chunking based on embedding similarity."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        similarity_threshold: float = 0.5,
    ):
        """Initialize semantic chunker.
        
        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks
            similarity_threshold: Threshold for semantic similarity
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold
    
    def chunk(self, documents: list[Any]) -> list[Chunk]:
        """Chunk documents semantically.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        
        for doc in documents:
            doc_chunks = self._chunk_document(doc)
            chunks.extend(doc_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks
    
    def _chunk_document(self, document: Any) -> list[Chunk]:
        """Chunk a single document.
        
        Args:
            document: Document object
            
        Returns:
            List of Chunk objects
        """
        # Split into sentences (simplified - use NLTK or spaCy in production)
        sentences = self._split_sentences(document.content)
        
        if len(sentences) <= 1:
            # Single sentence - create one chunk
            return [self._create_chunk(document, 0, document.content)]
        
        # Calculate embeddings for sentences
        embeddings = self._get_embeddings(sentences)
        
        # Find breakpoints based on semantic similarity
        breakpoints = self._find_breakpoints(sentences, embeddings)
        
        # Create chunks
        chunks = []
        start_idx = 0
        
        for breakpoint in breakpoints:
            chunk_content = " ".join(sentences[start_idx:breakpoint])
            
            # Check token count
            if self._count_tokens(chunk_content) > self.chunk_size * 2:
                # Too large - split further
                sub_chunks = self._split_large_chunk(document, start_idx, breakpoint, sentences)
                chunks.extend(sub_chunks)
            else:
                chunk = self._create_chunk(document, start_idx, chunk_content)
                chunks.append(chunk)
            
            start_idx = breakpoint
        
        # Add final chunk
        if start_idx < len(sentences):
            chunk_content = " ".join(sentences[start_idx:])
            chunk = self._create_chunk(document, start_idx, chunk_content)
            chunks.append(chunk)
        
        return chunks
    
    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Simplified - use NLTK or spaCy in production
        sentences = text.split(". ")
        return [s.strip() + "." for s in sentences if s.strip()]
    
    def _get_embeddings(self, sentences: list[str]) -> np.ndarray:
        """Get embeddings for sentences.
        
        Args:
            sentences: List of sentences
            
        Returns:
            Embeddings array
        """
        # Simplified - use actual embedding model in production
        # Return random embeddings for demo
        return np.random.rand(len(sentences), 384)
    
    def _find_breakpoints(self, sentences: list[str], embeddings: np.ndarray) -> list[int]:
        """Find chunk breakpoints based on semantic similarity.
        
        Args:
            sentences: List of sentences
            embeddings: Sentence embeddings
            
        Returns:
            List of breakpoint indices
        """
        if len(embeddings) <= 1:
            return [len(sentences)]
        
        # Calculate cosine similarities
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)
        
        # Find breakpoints where similarity drops below threshold
        breakpoints = []
        current_chunk_size = 0
        
        for i, sim in enumerate(similarities):
            current_chunk_size += 1
            
            # Break if similarity is low or chunk is too large
            if sim < self.similarity_threshold or current_chunk_size >= self.chunk_size:
                breakpoints.append(i + 1)
                current_chunk_size = 0
        
        # Ensure we have at least one breakpoint
        if not breakpoints:
            breakpoints = [len(sentences)]
        
        return breakpoints
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity.
        
        Args:
            a: Vector a
            b: Vector b
            
        Returns:
            Cosine similarity
        """
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def _create_chunk(self, document: Any, start_idx: int, content: str) -> Chunk:
        """Create chunk from document.
        
        Args:
            document: Source document
            start_idx: Starting sentence index
            content: Chunk content
            
        Returns:
            Chunk object
        """
        return Chunk(
            id=f"{document.id}_chunk_{start_idx}",
            content=content,
            metadata=document.metadata.copy(),
            source_id=document.id,
            chunk_index=start_idx,
            start_char=0,
            end_char=len(content),
            token_count=self._count_tokens(content),
        )
    
    def _split_large_chunk(
        self,
        document: Any,
        start_idx: int,
        end_idx: int,
        sentences: list[str],
    ) -> list[Chunk]:
        """Split large chunk into smaller chunks.
        
        Args:
            document: Source document
            start_idx: Start sentence index
            end_idx: End sentence index
            sentences: List of sentences
            
        Returns:
            List of chunks
        """
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for i in range(start_idx, end_idx):
            sentence = sentences[i]
            sentence_tokens = self._count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Create chunk
                content = " ".join(current_chunk)
                chunk = self._create_chunk(document, start_idx, content)
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk[-self.chunk_overlap:] if self.chunk_overlap > 0 else []
                current_chunk = overlap_sentences + [sentence]
                current_tokens = sum(self._count_tokens(s) for s in current_chunk)
                start_idx = i
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            content = " ".join(current_chunk)
            chunk = self._create_chunk(document, start_idx, content)
            chunks.append(chunk)
        
        return chunks
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text.
        
        Args:
            text: Text to count
            
        Returns:
            Token count
        """
        # Simplified - use tiktoken in production
        return len(text.split())


class FixedSizeChunker:
    """Fixed-size chunking with overlap."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        """Initialize fixed-size chunker.
        
        Args:
            chunk_size: Chunk size in tokens
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk(self, documents: list[Any]) -> list[Chunk]:
        """Chunk documents into fixed-size chunks.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        
        for doc in documents:
            doc_chunks = self._chunk_document(doc)
            chunks.extend(doc_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks
    
    def _chunk_document(self, document: Any) -> list[Chunk]:
        """Chunk a single document.
        
        Args:
            document: Document object
            
        Returns:
            List of Chunk objects
        """
        tokens = document.content.split()
        chunks = []
        
        start_idx = 0
        chunk_idx = 0
        
        while start_idx < len(tokens):
            # Get chunk
            end_idx = min(start_idx + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_content = " ".join(chunk_tokens)
            
            # Create chunk
            chunk = Chunk(
                id=f"{document.id}_chunk_{chunk_idx}",
                content=chunk_content,
                metadata=document.metadata.copy(),
                source_id=document.id,
                chunk_index=chunk_idx,
                start_char=start_idx,
                end_char=end_idx,
                token_count=len(chunk_tokens),
            )
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start_idx += self.chunk_size - self.chunk_overlap
            chunk_idx += 1
        
        return chunks


class RecursiveChunker:
    """Recursive chunking with parent-child relationships."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: list[str] = None,
    ):
        """Initialize recursive chunker.
        
        Args:
            chunk_size: Chunk size in tokens
            chunk_overlap: Overlap between chunks
            separators: List of separators for splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
    
    def chunk(self, documents: list[Any]) -> list[Chunk]:
        """Chunk documents recursively.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        
        for doc in documents:
            doc_chunks = self._chunk_document(doc)
            chunks.extend(doc_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks
    
    def _chunk_document(self, document: Any) -> list[Chunk]:
        """Chunk a single document recursively.
        
        Args:
            document: Document object
            
        Returns:
            List of Chunk objects
        """
        return self._split_text(document, document.content, 0)
    
    def _split_text(self, document: Any, text: str, depth: int) -> list[Chunk]:
        """Split text recursively.
        
        Args:
            document: Source document
            text: Text to split
            depth: Current recursion depth
            
        Returns:
            List of Chunk objects
        """
        # If text is small enough, return as single chunk
        if len(text.split()) <= self.chunk_size:
            return [self._create_chunk(document, 0, text)]
        
        # Get separator for current depth
        separator = self.separators[min(depth, len(self.separators) - 1)]
        
        # Split by separator
        if separator:
            parts = text.split(separator)
        else:
            parts = [text]
        
        # Combine parts into chunks
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i, part in enumerate(parts):
            part_length = len(part.split())
            
            if current_length + part_length > self.chunk_size and current_chunk:
                # Create chunk
                chunk_content = separator.join(current_chunk)
                chunk = self._create_chunk(document, i, chunk_content)
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_parts = current_chunk[-self.chunk_overlap:] if self.chunk_overlap > 0 else []
                current_chunk = overlap_parts + [part]
                current_length = sum(len(p.split()) for p in current_chunk)
            else:
                current_chunk.append(part)
                current_length += part_length
        
        # Add final chunk
        if current_chunk:
            chunk_content = separator.join(current_chunk)
            chunk = self._create_chunk(document, len(parts), chunk_content)
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(self, document: Any, index: int, content: str) -> Chunk:
        """Create chunk from document.
        
        Args:
            document: Source document
            index: Chunk index
            content: Chunk content
            
        Returns:
            Chunk object
        """
        return Chunk(
            id=f"{document.id}_chunk_{index}",
            content=content,
            metadata=document.metadata.copy(),
            source_id=document.id,
            chunk_index=index,
            start_char=0,
            end_char=len(content),
            token_count=len(content.split()),
        )