"""
Enterprise Reference Architecture Validator

This module validates that the enterprise architecture artifacts
are complete and consistent across all projects.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import os
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation levels"""
    CRITICAL = "critical"
    REQUIRED = "required"
    RECOMMENDED = "recommended"


class ArtifactStatus(str, Enum):
    """Artifact status"""
    COMPLETE = "complete"
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    NOT_APPLICABLE = "not_applicable"


class ArchitectureArtifact(BaseModel):
    """Architecture artifact definition"""
    artifact_id: str
    name: str
    category: str
    required_path: str
    validation_level: ValidationLevel
    status: ArtifactStatus = ArtifactStatus.MISSING
    notes: Optional[str] = None


class ValidationResult(BaseModel):
    """Validation result"""
    artifact_id: str
    name: str
    status: ArtifactStatus
    validation_level: ValidationLevel
    notes: Optional[str] = None
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class EnterpriseValidator:
    """
    Validates the completeness of the enterprise reference architecture
    
    This service validates:
    - Architecture documentation
    - Reference implementations
    - ADRs
    - Standards
    - Dashboards
    - CI/CD
    """
    
    REQUIRED_ARTIFACTS = [
        ArchitectureArtifact(
            artifact_id="README",
            name="Project README",
            category="documentation",
            required_path="README.md",
            validation_level=ValidationLevel.CRITICAL
        ),
        ArchitectureArtifact(
            artifact_id="EXEC_SUMMARY",
            name="Executive Summary",
            category="documentation",
            required_path="executive-summary.md",
            validation_level=ValidationLevel.CRITICAL
        ),
        ArchitectureArtifact(
            artifact_id="ARCHITECTURE",
            name="Enterprise Architecture",
            category="documentation",
            required_path="architecture.md",
            validation_level=ValidationLevel.CRITICAL
        ),
        ArchitectureArtifact(
            artifact_id="ADR",
            name="Architecture Decision Records",
            category="documentation",
            required_path="architecture-decision-records/",
            validation_level=ValidationLevel.CRITICAL
        ),
        ArchitectureArtifact(
            artifact_id="DIAGRAM",
            name="Architecture Diagram",
            category="documentation",
            required_path="diagrams/",
            validation_level=ValidationLevel.REQUIRED
        ),
        ArchitectureArtifact(
            artifact_id="REQUIREMENTS",
            name="Requirements",
            category="documentation",
            required_path="requirements.txt",
            validation_level=ValidationLevel.REQUIRED
        ),
        ArchitectureArtifact(
            artifact_id="GOVERNANCE",
            name="Governance Framework",
            category="governance",
            required_path="governance.md",
            validation_level=ValidationLevel.CRITICAL
        ),
        ArchitectureArtifact(
            artifact_id="SECURITY",
            name="Security Framework",
            category="security",
            required_path="security.md",
            validation_level=ValidationLevel.CRITICAL
        ),
        ArchitectureArtifact(
            artifact_id="OPERATIONS",
            name="Operations Manual",
            category="operations",
            required_path="operations.md",
            validation_level=ValidationLevel.REQUIRED
        ),
        ArchitectureArtifact(
            artifact_id="DEPLOYMENT",
            name="Deployment Guide",
            category="operations",
            required_path="deployment-guide.md",
            validation_level=ValidationLevel.REQUIRED
        ),
        ArchitectureArtifact(
            artifact_id="DR",
            name="Disaster Recovery",
            category="operations",
            required_path="disaster-recovery.md",
            validation_level=ValidationLevel.REQUIRED
        ),
    ]
    
    def __init__(self, base_path: str):
        """Initialize validator"""
        self.base_path = base_path
        self.results: List[ValidationResult] = []
    
    def validate(self) -> Dict[str, Any]:
        """Validate all artifacts"""
        logger.info(f"Validating enterprise architecture at: {self.base_path}")
        
        for artifact in self.REQUIRED_ARTIFACTS:
            path = os.path.join(self.base_path, artifact.required_path)
            exists = os.path.exists(path)
            
            status = ArtifactStatus.COMPLETE if exists else ArtifactStatus.MISSING
            
            result = ValidationResult(
                artifact_id=artifact.artifact_id,
                name=artifact.name,
                status=status,
                validation_level=artifact.validation_level,
                notes=f"Path: {artifact.required_path}" if exists else "Artifact not found"
            )
            
            self.results.append(result)
        
        return self.get_summary()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        total = len(self.results)
        complete = len([r for r in self.results if r.status == ArtifactStatus.COMPLETE])
        missing = len([r for r in self.results if r.status == ArtifactStatus.MISSING])
        
        critical = [r for r in self.results if r.validation_level == ValidationLevel.CRITICAL]
        critical_complete = len([r for r in critical if r.status == ArtifactStatus.COMPLETE])
        
        completion_rate = (complete / total * 100) if total > 0 else 0
        
        return {
            "total_artifacts": total,
            "complete": complete,
            "missing": missing,
            "completion_rate": completion_rate,
            "critical_complete": critical_complete,
            "critical_total": len(critical),
            "critical_ready": critical_complete == len(critical),
            "results": [r.model_dump() for r in self.results]
        }
    
    def validate_project_integration(self, projects: List[Dict[str, str]]) -> Dict[str, Any]:
        """Validate integration with prior projects"""
        project_status = []
        
        for project in projects:
            project_id = project.get("project_id", "")
            name = project.get("name", "")
            path = project.get("path", "")
            
            exists = os.path.exists(path)
            
            project_status.append({
                "project_id": project_id,
                "name": name,
                "path": path,
                "ready": exists,
                "status": "ready" if exists else "missing"
            })
        
        ready = len([p for p in project_status if p["ready"]])
        
        return {
            "total_projects": len(projects),
            "ready_projects": ready,
            "integration_rate": (ready / len(projects) * 100) if projects else 0,
            "projects": project_status
        }


PROJECTS_01_29 = [
    {"project_id": "01", "name": "Python Fundamentals", "path": "projects/01_python_fundamentals"},
    {"project_id": "02", "name": "SQL for Data Engineering", "path": "projects/02_sql_for_data_engineering"},
    {"project_id": "04", "name": "Python ETL Framework", "path": "projects/04_python_etl_framework"},
    {"project_id": "07", "name": "Enterprise PySpark", "path": "projects/07_enterprise_pyspark"},
    {"project_id": "08", "name": "Delta Lake", "path": "projects/08_delta_lake"},
    {"project_id": "10", "name": "Databricks Lakehouse", "path": "projects/10_enterprise_databricks_lakehouse"},
    {"project_id": "11", "name": "Apache Airflow", "path": "projects/11_enterprise_apache_airflow"},
    {"project_id": "12", "name": "Apache Kafka", "path": "projects/12_enterprise_apache_kafka"},
    {"project_id": "13", "name": "Spark Streaming", "path": "projects/13_enterprise_spark_structured_streaming"},
    {"project_id": "14", "name": "dbt Analytics", "path": "projects/14_enterprise_dbt_analytics_engineering"},
    {"project_id": "15", "name": "Snowflake", "path": "projects/15_enterprise_snowflake_data_cloud"},
    {"project_id": "21", "name": "Data Mesh", "path": "projects/21_enterprise_data_mesh"},
    {"project_id": "22", "name": "Data Fabric", "path": "projects/22_enterprise_data_fabric"},
    {"project_id": "23", "name": "MLOps & Features", "path": "projects/23_enterprise_mlops_feature_platform"},
    {"project_id": "24", "name": "Real-Time AI", "path": "projects/24_enterprise_real_time_ai_platform"},
    {"project_id": "25", "name": "Data Platform SRE", "path": "projects/25_enterprise_data_platform_sre"},
    {"project_id": "26", "name": "Platform Engineering", "path": "projects/26_enterprise_platform_engineering"},
    {"project_id": "27", "name": "Security & Privacy", "path": "projects/27_enterprise_data_security_privacy"},
    {"project_id": "28", "name": "Multi-Cloud Platform", "path": "projects/28_enterprise_multicloud_data_platform"},
    {"project_id": "29", "name": "Agentic AI", "path": "projects/29_enterprise_agentic_ai_data_platform"},
]