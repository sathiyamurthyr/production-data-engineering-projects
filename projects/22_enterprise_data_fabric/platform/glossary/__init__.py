"""Business Glossary - Term definitions and relationships."""

from .models import Term, Category
from .service import GlossaryService

__all__ = ["Term", "Category", "GlossaryService"]