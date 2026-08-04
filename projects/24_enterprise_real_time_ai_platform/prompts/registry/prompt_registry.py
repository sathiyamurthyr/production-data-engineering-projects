"""Prompt Registry - Version and manage AI prompts."""

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PromptTemplate(BaseModel):
    """Prompt template."""
    id: str
    name: str
    description: str
    template: str
    variables: list[str]
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime
    created_by: str
    version: str
    is_active: bool = True


class PromptRegistry:
    """Registry for prompt templates."""
    
    def __init__(self):
        """Initialize prompt registry."""
        self.prompts: dict[str, PromptTemplate] = {}
        self.versions: dict[str, list[PromptTemplate]] = {}
    
    def register(self, prompt: PromptTemplate) -> None:
        """Register prompt template.
        
        Args:
            prompt: Prompt template
        """
        self.prompts[prompt.id] = prompt
        
        if prompt.id not in self.versions:
            self.versions[prompt.id] = []
        
        self.versions[prompt.id].append(prompt)
        
        logger.info(f"Registered prompt: {prompt.id} v{prompt.version}")
    
    def get_prompt(self, prompt_id: str, version: str = None) -> PromptTemplate | None:
        """Get prompt template.
        
        Args:
            prompt_id: Prompt ID
            version: Version (optional)
            
        Returns:
            Prompt template or None
        """
        if version:
            # Get specific version
            versions = self.versions.get(prompt_id, [])
            for v in versions:
                if v.version == version:
                    return v
            return None
        else:
            # Get latest active version
            return self.prompts.get(prompt_id)
    
    def list_prompts(self, tag: str = None) -> list[PromptTemplate]:
        """List all prompts.
        
        Args:
            tag: Filter by tag (optional)
            
        Returns:
            List of prompts
        """
        prompts = list(self.prompts.values())
        
        if tag:
            prompts = [p for p in prompts if tag in p.tags]
        
        return prompts
    
    def render(self, prompt_id: str, variables: dict[str, str], version: str = None) -> str:
        """Render prompt template with variables.
        
        Args:
            prompt_id: Prompt ID
            variables: Template variables
            version: Version (optional)
            
        Returns:
            Rendered prompt
        """
        prompt = self.get_prompt(prompt_id, version)
        
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_id}")
        
        # Render template
        rendered = prompt.template
        
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            rendered = rendered.replace(placeholder, str(value))
        
        # Check for missing variables
        import re
        missing = re.findall(r'\{(\w+)\}', rendered)
        if missing:
            logger.warning(f"Missing variables in prompt {prompt_id}: {missing}")
        
        return rendered
    
    def deactivate(self, prompt_id: str) -> bool:
        """Deactivate prompt.
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            True if successful
        """
        if prompt_id not in self.prompts:
            return False
        
        self.prompts[prompt_id].is_active = False
        return True


class PromptEvaluator:
    """Evaluate prompt performance."""
    
    def __init__(self):
        """Initialize prompt evaluator."""
        self.evaluations: dict[str, list[dict[str, Any]]] = {}
    
    def evaluate(
        self,
        prompt_id: str,
        version: str,
        metrics: dict[str, float],
        feedback: str = None,
    ) -> dict[str, Any]:
        """Evaluate prompt.
        
        Args:
            prompt_id: Prompt ID
            version: Version
            metrics: Evaluation metrics
            feedback: User feedback
            
        Returns:
            Evaluation result
        """
        evaluation = {
            "prompt_id": prompt_id,
            "version": version,
            "timestamp": datetime.now(),
            "metrics": metrics,
            "feedback": feedback,
        }
        
        if prompt_id not in self.evaluations:
            self.evaluations[prompt_id] = []
        
        self.evaluations[prompt_id].append(evaluation)
        
        logger.info(f"Evaluated prompt: {prompt_id} v{version}")
        
        return evaluation
    
    def get_evaluations(self, prompt_id: str) -> list[dict[str, Any]]:
        """Get evaluations for prompt.
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            List of evaluations
        """
        return self.evaluations.get(prompt_id, [])
    
    def get_best_version(self, prompt_id: str, metric: str = "relevance") -> str | None:
        """Get best performing version.
        
        Args:
            prompt_id: Prompt ID
            metric: Metric to optimize
            
        Returns:
            Best version or None
        """
        evaluations = self.evaluations.get(prompt_id, [])
        
        if not evaluations:
            return None
        
        # Find version with highest metric
        best_version = max(
            evaluations,
            key=lambda e: e["metrics"].get(metric, 0)
        )
        
        return best_version["version"]


class PromptVersionManager:
    """Manage prompt versions."""
    
    def __init__(self):
        """Initialize version manager."""
        self.version_history: dict[str, list[dict[str, Any]]] = {}
    
    def create_version(
        self,
        prompt_id: str,
        version: str,
        changes: str,
        author: str,
    ) -> dict[str, Any]:
        """Create new version.
        
        Args:
            prompt_id: Prompt ID
            version: Version string
            changes: Description of changes
            author: Version author
            
        Returns:
            Version info
        """
        version_info = {
            "version": version,
            "changes": changes,
            "author": author,
            "created_at": datetime.now(),
        }
        
        if prompt_id not in self.version_history:
            self.version_history[prompt_id] = []
        
        self.version_history[prompt_id].append(version_info)
        
        logger.info(f"Created version {version} for prompt {prompt_id}")
        
        return version_info
    
    def get_version_history(self, prompt_id: str) -> list[dict[str, Any]]:
        """Get version history.
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            Version history
        """
        return self.version_history.get(prompt_id, [])
    
    def compare_versions(
        self,
        prompt_id: str,
        version1: str,
        version2: str,
    ) -> dict[str, Any]:
        """Compare two versions.
        
        Args:
            prompt_id: Prompt ID
            version1: First version
            version2: Second version
            
        Returns:
            Comparison result
        """
        versions = self.version_history.get(prompt_id, [])
        
        v1_info = next((v for v in versions if v["version"] == version1), None)
        v2_info = next((v for v in versions if v["version"] == version2), None)
        
        if not v1_info or not v2_info:
            return {"error": "Version not found"}
        
        return {
            "prompt_id": prompt_id,
            "version1": {
                "version": v1_info["version"],
                "created_at": v1_info["created_at"],
                "author": v1_info["author"],
                "changes": v1_info["changes"],
            },
            "version2": {
                "version": v2_info["version"],
                "created_at": v2_info["created_at"],
                "author": v2_info["author"],
                "changes": v2_info["changes"],
            },
        }


class PromptTemplateLibrary:
    """Library of pre-built prompt templates."""
    
    def __init__(self):
        """Initialize template library."""
        self.templates: dict[str, str] = {
            "rag_qa": """Answer the question based on the context below.

Context:
{context}

Question: {question}

Answer:""",
            
            "summarize": """Summarize the following text:

{text}

Summary:""",
            
            "extract_entities": """Extract all entities from the following text and categorize them.

Text: {text}

Entities:""",
            
            "code_review": """Review the following code and provide feedback:

{code}

Review:""",
            
            "sql_generation": """Generate a SQL query to answer the following question:

Question: {question}

Schema:
{schema}

SQL Query:""",
        }
    
    def get_template(self, template_name: str) -> str | None:
        """Get template by name.
        
        Args:
            template_name: Template name
            
        Returns:
            Template string or None
        """
        return self.templates.get(template_name)
    
    def register_template(self, name: str, template: str) -> None:
        """Register custom template.
        
        Args:
            name: Template name
            template: Template string
        """
        self.templates[name] = template
        logger.info(f"Registered template: {name}")
    
    def list_templates(self) -> list[str]:
        """List all templates.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())