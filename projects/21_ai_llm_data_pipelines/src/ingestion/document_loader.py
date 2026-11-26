"""Document ingestion loaders for Markdown, TXT, JSONL, and CSV sources."""

import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from src.models import RawDocument


def compute_sha256(text: str) -> str:
    """Compute a deterministic SHA-256 hex digest for content change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentLoader:
    """Loads heterogeneous unstructured and semi-structured sources into RawDocuments."""

    SUPPORTED_EXTENSIONS = {".md", ".txt", ".jsonl", ".csv"}

    def __init__(self, default_acl_group: str = "engineering") -> None:
        self.default_acl_group = default_acl_group

    def load_directory(self, directory: str | Path) -> List[RawDocument]:
        """Recursively load all supported documents from a directory sorted deterministically."""
        root = Path(directory)
        if not root.exists():
            raise FileNotFoundError(f"Source directory does not exist: {root}")

        documents: List[RawDocument] = []
        for file_path in sorted(root.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                documents.extend(self.load_file(file_path))
        return documents

    def load_file(self, file_path: str | Path) -> List[RawDocument]:
        """Dispatch file loading based on extension."""
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension '{ext}' for {path}")

        if ext in {".md", ".txt"}:
            return [self._load_text_file(path)]
        if ext == ".jsonl":
            return self._load_jsonl_file(path)
        return self._load_csv_file(path)

    def _load_text_file(self, path: Path) -> RawDocument:
        content = path.read_text(encoding="utf-8")
        title = self._extract_markdown_title(content) or path.stem.replace("_", " ").title()
        return RawDocument(
            doc_id=path.name,
            source_uri=str(path),
            title=title,
            content=content,
            content_hash=compute_sha256(content),
            acl_group=self.default_acl_group,
            source_type="markdown" if path.suffix.lower() == ".md" else "text",
            metadata={"file_name": path.name, "extension": path.suffix.lower()},
        )

    def _load_jsonl_file(self, path: Path) -> List[RawDocument]:
        docs: List[RawDocument] = []
        with path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                record: Dict[str, object] = json.loads(stripped)
                doc_id = str(record.get("doc_id") or f"{path.name}:{idx}")
                title = str(record.get("title") or doc_id)
                text = str(record.get("text") or record.get("content") or "")
                acl_group = str(record.get("acl_group") or self.default_acl_group)
                extra_meta = {
                    k: v
                    for k, v in record.items()
                    if k not in {"doc_id", "title", "text", "content", "acl_group"}
                }
                docs.append(
                    RawDocument(
                        doc_id=doc_id,
                        source_uri=f"{path}#line={idx}",
                        title=title,
                        content=f"# {title}\n\n{text}" if title else text,
                        content_hash=compute_sha256(f"{title}\n{text}"),
                        acl_group=acl_group,
                        source_type="jsonl",
                        metadata=extra_meta,
                    )
                )
        return docs

    def _load_csv_file(self, path: Path) -> List[RawDocument]:
        docs: List[RawDocument] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for idx, row in enumerate(reader, start=1):
                doc_id = (row.get("doc_id") or row.get("id") or f"{path.name}:{idx}").strip()
                title = (row.get("title") or row.get("subject") or doc_id).strip()
                body = (row.get("text") or row.get("content") or row.get("body") or "").strip()
                acl_group = (row.get("acl_group") or self.default_acl_group).strip()
                content = f"# {title}\n\n{body}" if title else body
                docs.append(
                    RawDocument(
                        doc_id=doc_id,
                        source_uri=f"{path}#row={idx}",
                        title=title,
                        content=content,
                        content_hash=compute_sha256(content),
                        acl_group=acl_group,
                        source_type="csv",
                        metadata={"row_number": idx},
                    )
                )
        return docs

    @staticmethod
    def _extract_markdown_title(content: str) -> Optional[str]:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return None
