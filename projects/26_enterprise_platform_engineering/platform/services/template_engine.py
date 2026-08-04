"""
Template Engine Service
Manages golden path templates, rendering, and validation
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
from pathlib import Path
import jinja2
import yaml
import json
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Integer
import uuid

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql+asyncpg://platform:platform@platform-postgres:5432/platform"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Template storage path
TEMPLATE_STORAGE_PATH = Path("/templates")


# ============================================================================
# Database Models
# ============================================================================

class TemplateModel(Base):
    """Template database model."""
    __tablename__ = "templates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    description = Column(Text)
    version = Column(String, default="1.0.0")
    author = Column(String)
    tags = Column(JSON)
    schema = Column(JSON)  # Template variable schema
    files = Column(JSON)  # List of template files
    status = Column(String, default="active")  # active, deprecated, draft
    downloads = Column(Integer, default=0)
    rating = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TemplateVariableModel(Base):
    """Template variable database model."""
    __tablename__ = "template_variables"

    id = Column(String, primary_key=True)
    template_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    type = Column(String)  # string, number, boolean, array, object
    required = Column(Boolean, default=False)
    default = Column(JSON)
    validation = Column(JSON)  # Validation rules
    created_at = Column(DateTime, default=datetime.utcnow)


class TemplateVersionModel(Base):
    """Template version database model."""
    __tablename__ = "template_versions"

    id = Column(String, primary_key=True)
    template_id = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False)
    content = Column(JSON)  # Template files content
    changelog = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)


# ============================================================================
# Pydantic Models
# ============================================================================

class TemplateVariable(BaseModel):
    """Template variable model."""
    name: str
    description: str
    type: str
    required: bool = False
    default: Optional[Any] = None
    validation: Dict[str, Any] = {}


class TemplateFile(BaseModel):
    """Template file model."""
    path: str
    content: str
    permissions: Optional[str] = None


class Template(BaseModel):
    """Template model."""
    id: str
    name: str
    category: str
    description: str
    version: str
    author: str
    tags: List[str]
    schema: Dict[str, Any]
    files: List[TemplateFile]
    status: str
    downloads: int
    rating: int
    created_at: datetime
    updated_at: datetime


class TemplateCreate(BaseModel):
    """Template creation request."""
    name: str
    category: str
    description: str
    version: str = "1.0.0"
    author: str
    tags: List[str] = []
    schema: Dict[str, Any]
    files: List[TemplateFile]


class TemplateRenderRequest(BaseModel):
    """Template render request."""
    template_id: str
    variables: Dict[str, Any]


class ValidationError(BaseModel):
    """Validation error model."""
    field: str
    message: str
    code: str


class ValidationResult(BaseModel):
    """Validation result model."""
    valid: bool
    errors: List[ValidationError]


class RenderedTemplate(BaseModel):
    """Rendered template result."""
    content: Dict[str, str]
    files: List[TemplateFile]


# ============================================================================
# Template Engine Service
# ============================================================================

class TemplateEngineService:
    """Template engine management service."""

    def __init__(self):
        self.templates: Dict[str, Template] = {}
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(TEMPLATE_STORAGE_PATH)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )

    async def initialize(self):
        """Initialize template engine."""
        logger.info("Initializing template engine...")

        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create template storage directory
        TEMPLATE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

        # Load templates from database
        await self._load_templates()

        logger.info(f"Template engine initialized with {len(self.templates)} templates")

    async def _load_templates(self):
        """Load templates from database."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(TemplateModel))
            templates = result.scalars().all()

            for tmpl in templates:
                template = Template(
                    id=tmpl.id,
                    name=tmpl.name,
                    category=tmpl.category,
                    description=tmpl.description,
                    version=tmpl.version,
                    author=tmpl.author,
                    tags=tmpl.tags or [],
                    schema=tmpl.schema or {},
                    files=[],  # Load from file storage
                    status=tmpl.status,
                    downloads=tmpl.downloads,
                    rating=tmpl.rating,
                    created_at=tmpl.created_at,
                    updated_at=tmpl.updated_at
                )
                self.templates[tmpl.id] = template

    async def health_check(self) -> Dict[str, str]:
        """Health check for template engine."""
        try:
            # Test database connection
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                await session.execute(select(TemplateModel).limit(1))

            return {
                "status": "healthy",
                "template_count": str(len(self.templates)),
                "storage_path": str(TEMPLATE_STORAGE_PATH)
            }
        except Exception as e:
            logger.error(f"Template engine health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Template]:
        """
        List all templates with optional filters.
        
        Args:
            category: Filter by category
            tags: Filter by tags (any match)
            
        Returns:
            List of templates
        """
        templates = list(self.templates.values())

        # Apply filters
        if category:
            templates = [t for t in templates if t.category == category]

        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]

        return templates

    async def get_template(self, template_id: str) -> Optional[Template]:
        """
        Get template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template or None if not found
        """
        return self.templates.get(template_id)

    async def create_template(self, request: TemplateCreate) -> Template:
        """
        Create a new template.
        
        Args:
            request: Template creation request
            
        Returns:
            Created template
        """
        template_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Create database record
        async with AsyncSessionLocal() as session:
            template_model = TemplateModel(
                id=template_id,
                name=request.name,
                category=request.category,
                description=request.description,
                version=request.version,
                author=request.author,
                tags=request.tags,
                schema=request.schema,
                files=[f.dict() for f in request.files],
                created_at=now,
                updated_at=now
            )
            session.add(template_model)
            await session.commit()

        # Save template files to storage
        template_dir = TEMPLATE_STORAGE_PATH / template_id
        template_dir.mkdir(parents=True, exist_ok=True)

        for file in request.files:
            file_path = template_dir / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.content)

        # Create template object
        template = Template(
            id=template_id,
            name=request.name,
            category=request.category,
            description=request.description,
            version=request.version,
            author=request.author,
            tags=request.tags,
            schema=request.schema,
            files=request.files,
            status="active",
            downloads=0,
            rating=0,
            created_at=now,
            updated_at=now
        )

        # Add to cache
        self.templates[template_id] = template

        logger.info(f"Created template: {template_id} - {request.name}")
        return template

    async def validate_variables(
        self,
        template_id: str,
        variables: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate template variables against schema.
        
        Args:
            template_id: Template identifier
            variables: Variables to validate
            
        Returns:
            Validation result
        """
        template = self.templates.get(template_id)
        if not template:
            return ValidationResult(
                valid=False,
                errors=[ValidationError(
                    field="template_id",
                    message=f"Template {template_id} not found",
                    code="TEMPLATE_NOT_FOUND"
                )]
            )

        errors = []
        schema = template.schema

        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in variables:
                errors.append(ValidationError(
                    field=field,
                    message=f"Required field '{field}' is missing",
                    code="REQUIRED_FIELD_MISSING"
                ))

        # Validate each field
        properties = schema.get("properties", {})
        for field_name, field_schema in properties.items():
            if field_name in variables:
                value = variables[field_name]
                field_type = field_schema.get("type")

                # Type validation
                if not self._validate_type(value, field_type):
                    errors.append(ValidationError(
                        field=field_name,
                        message=f"Invalid type for '{field_name}'. Expected {field_type}",
                        code="INVALID_TYPE"
                    ))

                # Custom validation
                validation_rules = field_schema.get("validation", {})
                for rule_name, rule_value in validation_rules.items():
                    if not self._apply_validation(value, rule_name, rule_value):
                        errors.append(ValidationError(
                            field=field_name,
                            message=f"Validation failed for '{field_name}': {rule_name}",
                            code=f"VALIDATION_{rule_name.upper()}"
                        ))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True

        return isinstance(value, expected)

    def _apply_validation(self, value: Any, rule: str, rule_value: Any) -> bool:
        """Apply validation rule."""
        if rule == "min_length":
            return len(value) >= rule_value
        elif rule == "max_length":
            return len(value) <= rule_value
        elif rule == "pattern":
            import re
            return bool(re.match(rule_value, value))
        elif rule == "minimum":
            return value >= rule_value
        elif rule == "maximum":
            return value <= rule_value
        elif rule == "enum":
            return value in rule_value

        return True

    async def render(
        self,
        template_id: str,
        variables: Dict[str, Any],
        user: Optional[Any] = None
    ) -> RenderedTemplate:
        """
        Render template with variables.
        
        Args:
            template_id: Template identifier
            variables: Variables for rendering
            user: User requesting render
            
        Returns:
            Rendered template
        """
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Validate variables
        validation_result = await self.validate_variables(template_id, variables)
        if not validation_result.valid:
            raise ValueError(f"Invalid variables: {validation_result.errors}")

        # Render each file
        rendered_files = []
        rendered_content = {}

        template_dir = TEMPLATE_STORAGE_PATH / template_id

        for file in template.files:
            file_path = template_dir / file.path
            content = file_path.read_text()

            # Render with Jinja2
            jinja_template = self.jinja_env.from_string(content)
            rendered = jinja_template.render(**variables, user=user)

            rendered_files.append(TemplateFile(
                path=file.path,
                content=rendered,
                permissions=file.permissions
            ))

            rendered_content[file.path] = rendered

        # Increment download counter
        template.downloads += 1
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            stmt = update(TemplateModel).where(TemplateModel.id == template_id).values(
                downloads=template.downloads
            )
            await session.execute(stmt)
            await session.commit()

        return RenderedTemplate(
            content=rendered_content,
            files=rendered_files
        )

    async def get_schema(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get template variable schema.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Schema or None if not found
        """
        template = self.templates.get(template_id)
        if not template:
            return None

        return template.schema

    async def get_categories(self) -> List[str]:
        """
        Get all template categories.
        
        Returns:
            List of unique categories
        """
        categories = set()
        for template in self.templates.values():
            categories.add(template.category)

        return sorted(list(categories))

    async def get_tags(self) -> List[str]:
        """
        Get all template tags.
        
        Returns:
            List of unique tags
        """
        tags = set()
        for template in self.templates.values():
            tags.update(template.tags)

        return sorted(list(tags))

    async def record_usage(
        self,
        template_id: str,
        user_id: str,
        success: bool,
        render_time_ms: int
    ):
        """
        Record template usage metrics.
        
        Args:
            template_id: Template identifier
            user_id: User identifier
            success: Whether rendering succeeded
            render_time_ms: Render time in milliseconds
        """
        logger.debug(
            f"Template usage: {template_id} by {user_id}, "
            f"success={success}, time={render_time_ms}ms"
        )

    async def create_version(
        self,
        template_id: str,
        version: str,
        content: Dict[str, str],
        changelog: str,
        created_by: str
    ) -> TemplateVersionModel:
        """
        Create new template version.
        
        Args:
            template_id: Template identifier
            version: Version string
            content: Template files content
            changelog: Version changelog
            created_by: Creator user ID
            
        Returns:
            Created template version
        """
        version_id = str(uuid.uuid4())
        now = datetime.utcnow()

        async with AsyncSessionLocal() as session:
            version_model = TemplateVersionModel(
                id=version_id,
                template_id=template_id,
                version=version,
                content=content,
                changelog=changelog,
                created_at=now,
                created_by=created_by
            )
            session.add(version_model)
            await session.commit()

        logger.info(f"Created template version: {template_id} v{version}")
        return version_model

    async def get_versions(self, template_id: str) -> List[TemplateVersionModel]:
        """
        Get all versions of a template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            List of template versions
        """
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = select(TemplateVersionModel).where(
                TemplateVersionModel.template_id == template_id
            ).order_by(TemplateVersionModel.created_at.desc())

            result = await session.execute(stmt)
            versions = result.scalars().all()

            return list(versions)

    async def deprecate_template(self, template_id: str):
        """
        Deprecate a template.
        
        Args:
            template_id: Template identifier
        """
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            stmt = update(TemplateModel).where(TemplateModel.id == template_id).values(
                status="deprecated",
                updated_at=datetime.utcnow()
            )
            await session.execute(stmt)
            await session.commit()

        # Update cache
        template = self.templates.get(template_id)
        if template:
            template.status = "deprecated"
            template.updated_at = datetime.utcnow()

        logger.info(f"Deprecated template: {template_id}")

    async def get_popular_templates(self, limit: int = 10) -> List[Template]:
        """
        Get most popular templates by downloads.
        
        Args:
            limit: Maximum number of templates to return
            
        Returns:
            List of popular templates
        """
        sorted_templates = sorted(
            self.templates.values(),
            key=lambda t: t.downloads,
            reverse=True
        )

        return sorted_templates[:limit]

    async def search_templates(self, query: str) -> List[Template]:
        """
        Search templates by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching templates
        """
        query_lower = query.lower()

        matches = [
            t for t in self.templates.values()
            if query_lower in t.name.lower()
            or query_lower in t.description.lower()
            or any(query_lower in tag.lower() for tag in t.tags)
        ]

        return matches