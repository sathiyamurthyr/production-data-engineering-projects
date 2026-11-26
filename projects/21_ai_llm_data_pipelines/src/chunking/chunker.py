"""Token-aware and Markdown-structure-aware document chunking."""

import hashlib
import re
from typing import List, Tuple

from src.models import SanitizedDocument, TextChunk


def estimate_tokens(text: str) -> int:
    """Fast deterministic token estimator (~1.3x whitespace-delimited words)."""
    words = text.split()
    if not words:
        return 0
    return max(1, int(round(len(words) * 1.25)))


class DocumentChunker:
    """Splits sanitized documents into overlapping chunks with heading provenance."""

    HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

    def __init__(
        self,
        strategy: str = "markdown_aware",
        max_tokens: int = 180,
        overlap_tokens: int = 30,
        min_chunk_tokens: int = 15,
    ) -> None:
        if strategy not in {"fixed", "markdown_aware"}:
            raise ValueError(f"Unsupported chunking strategy: {strategy}")
        if overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be strictly less than max_tokens")
        self.strategy = strategy
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens

    def chunk_document(self, doc: SanitizedDocument) -> List[TextChunk]:
        """Chunk a sanitized document according to the configured strategy."""
        if doc.quarantined or not doc.cleaned_content.strip():
            return []

        if self.strategy == "markdown_aware":
            sections = self._split_markdown_sections(doc.cleaned_content, default_title=doc.title)
        else:
            sections = [(doc.title, doc.cleaned_content)]

        chunks: List[TextChunk] = []
        chunk_index = 0
        for heading_path, body in sections:
            for piece in self._split_with_overlap(body):
                token_count = estimate_tokens(piece)
                if token_count < self.min_chunk_tokens and chunks:
                    # Merge tiny trailing fragment only if same heading or leave standalone if single
                    continue
                prefixed = f"[{heading_path}]\n{piece}" if heading_path else piece
                chunk_id = self._make_chunk_id(doc.doc_id, chunk_index, prefixed)
                chunks.append(
                    TextChunk(
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        chunk_index=chunk_index,
                        text=prefixed,
                        token_count=estimate_tokens(prefixed),
                        heading_path=heading_path,
                        acl_group=doc.acl_group,
                        source_uri=doc.source_uri,
                        content_hash=doc.content_hash,
                        metadata={**doc.metadata, "title": doc.title, "source_type": doc.source_type},
                    )
                )
                chunk_index += 1
        return chunks

    def _split_markdown_sections(self, content: str, default_title: str) -> List[Tuple[str, str]]:
        """Group lines under hierarchical Markdown heading paths."""
        sections: List[Tuple[str, str]] = []
        heading_stack: List[Tuple[int, str]] = []
        buffer: List[str] = []

        def flush() -> None:
            text = "\n".join(buffer).strip()
            if text:
                path = " > ".join(h for _, h in heading_stack) or default_title
                sections.append((path, text))
            buffer.clear()

        for line in content.splitlines():
            match = self.HEADING_RE.match(line.strip())
            if match:
                flush()
                level = len(match.group(1))
                title = match.group(2).strip()
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, title))
            else:
                buffer.append(line)

        flush()
        return sections or [(default_title, content.strip())]

    def _split_with_overlap(self, text: str) -> List[str]:
        """Split a section into word-window slices bounded by max_tokens."""
        words = text.split()
        if not words:
            return []

        max_words = max(1, int(self.max_tokens / 1.25))
        overlap_words = min(max_words - 1, int(self.overlap_tokens / 1.25))
        step = max(1, max_words - overlap_words)

        slices: List[str] = []
        for start in range(0, len(words), step):
            window = words[start : start + max_words]
            if not window:
                break
            slices.append(" ".join(window))
            if start + max_words >= len(words):
                break
        return slices

    @staticmethod
    def _make_chunk_id(doc_id: str, chunk_index: int, text: str) -> str:
        digest = hashlib.sha256(f"{doc_id}:{chunk_index}:{text}".encode("utf-8")).hexdigest()
        return f"{doc_id}::c{chunk_index:04d}::{digest[:12]}"
