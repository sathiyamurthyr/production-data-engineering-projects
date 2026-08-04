"""PDF Processor - Extract text and metadata from PDF documents."""

import logging
from pathlib import Path
from typing import Any

import pdfplumber
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Document(BaseModel):
    """Document representation."""
    id: str
    content: str
    metadata: dict[str, Any]
    source: str
    page_number: int | None = None


class PDFProcessor:
    """Process PDF documents and extract text."""
    
    def __init__(self, extract_tables: bool = False):
        """Initialize PDF processor.
        
        Args:
            extract_tables: Whether to extract tables from PDF
        """
        self.extract_tables = extract_tables
    
    def process(self, file_path: str) -> list[Document]:
        """Process PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of Document objects
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        documents = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text
                text = page.extract_text()
                
                if text and text.strip():
                    doc = Document(
                        id=f"{path.stem}_page_{page_num}",
                        content=text,
                        metadata={
                            "source": file_path,
                            "filename": path.name,
                            "page_number": page_num,
                            "total_pages": len(pdf.pages),
                        },
                        source=file_path,
                        page_number=page_num,
                    )
                    documents.append(doc)
                
                # Extract tables if enabled
                if self.extract_tables:
                    tables = page.extract_tables()
                    for table_num, table in enumerate(tables, start=1):
                        table_text = self._table_to_text(table)
                        if table_text:
                            doc = Document(
                                id=f"{path.stem}_page_{page_num}_table_{table_num}",
                                content=table_text,
                                metadata={
                                    "source": file_path,
                                    "filename": path.name,
                                    "page_number": page_num,
                                    "table_number": table_num,
                                    "type": "table",
                                },
                                source=file_path,
                                page_number=page_num,
                            )
                            documents.append(doc)
        
        logger.info(f"Processed {len(documents)} documents from {file_path}")
        return documents
    
    def _table_to_text(self, table: list[list[str]]) -> str:
        """Convert table to text.
        
        Args:
            table: Table data
            
        Returns:
            Table as text
        """
        if not table:
            return ""
        
        lines = []
        for row in table:
            if row:
                lines.append(" | ".join([cell or "" for cell in row]))
        
        return "\n".join(lines)


class OCRProcessor:
    """OCR processor for scanned PDFs."""
    
    def __init__(self, language: str = "eng"):
        """Initialize OCR processor.
        
        Args:
            language: Language for OCR
        """
        self.language = language
    
    def process_image(self, image_path: str) -> str:
        """Process image with OCR.
        
        Args:
            image_path: Path to image
            
        Returns:
            Extracted text
        """
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang=self.language)
            return text
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    def process_pdf_page(self, pdf_path: str, page_num: int) -> str:
        """Process PDF page with OCR.
        
        Args:
            pdf_path: Path to PDF
            page_num: Page number
            
        Returns:
            Extracted text
        """
        try:
            import pytesseract
            from PIL import Image
            import pdf2image
            
            # Convert PDF page to image
            images = pdf2images.convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
            
            if not images:
                return ""
            
            # OCR
            text = pytesseract.image_to_string(images[0], lang=self.language)
            return text
        except Exception as e:
            logger.error(f"PDF OCR failed: {e}")
            return ""


class DocumentMetadataExtractor:
    """Extract metadata from documents."""
    
    def extract(self, document: Document) -> dict[str, Any]:
        """Extract metadata from document.
        
        Args:
            document: Document object
            
        Returns:
            Metadata dictionary
        """
        metadata = document.metadata.copy()
        
        # Extract title (first line or heading)
        lines = document.content.split("\n")
        metadata["title"] = lines[0] if lines else ""
        
        # Extract word count
        metadata["word_count"] = len(document.content.split())
        
        # Extract character count
        metadata["char_count"] = len(document.content)
        
        # Extract language (simplified)
        metadata["language"] = self._detect_language(document.content)
        
        # Extract key phrases (simplified)
        metadata["key_phrases"] = self._extract_key_phrases(document.content)
        
        return metadata
    
    def _detect_language(self, text: str) -> str:
        """Detect document language.
        
        Args:
            text: Document text
            
        Returns:
            Language code
        """
        # Simplified - use langdetect library in production
        return "en"
    
    def _extract_key_phrases(self, text: str, top_k: int = 5) -> list[str]:
        """Extract key phrases from text.
        
        Args:
            text: Document text
            top_k: Number of key phrases
            
        Returns:
            List of key phrases
        """
        # Simplified - use RAKE, YAKE, or KeyBERT in production
        words = text.split()
        return words[:top_k]