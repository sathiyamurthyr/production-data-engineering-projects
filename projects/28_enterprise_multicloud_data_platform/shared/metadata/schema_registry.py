"""
Schema Registry for Cross-Cloud Data Management

This module provides unified schema management across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SchemaFormat(str, Enum):
    """Schema formats"""
    AVRO = "avro"
    PROTOBUF = "protobuf"
    JSON = "json"
    PARQUET = "parquet"
    DELTA = "delta"
    ICEBERG = "iceberg"
    SQL = "sql"


class SchemaVersion(BaseModel):
    """Schema version"""
    version_id: str
    schema_id: str
    version_number: int
    schema_definition: Dict[str, Any]
    format: SchemaFormat
    created_at: datetime
    created_by: str
    description: str
    compatibility_rules: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Schema(BaseModel):
    """Schema definition"""
    schema_id: str
    name: str
    namespace: str
    resource_type: str
    cloud: str
    description: str
    owner: str
    current_version: int
    versions: Dict[int, SchemaVersion]
    created_at: datetime
    updated_at: datetime
    tags: Dict[str, str] = Field(default_factory=dict)


class SchemaRegistry:
    """
    Cross-cloud schema registry
    
    This service provides:
    - Schema registration and versioning
    - Schema evolution management
    - Compatibility checking
    - Schema discovery
    """
    
    def __init__(self, config: Dict):
        """
        Initialize schema registry
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.schemas: Dict[str, Schema] = {}
        
        logger.info("Schema Registry initialized")
    
    async def register_schema(
        self,
        schema_id: str,
        name: str,
        namespace: str,
        resource_type: str,
        cloud: str,
        description: str,
        owner: str,
        schema_definition: Dict[str, Any],
        format: SchemaFormat,
        compatibility_rules: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Schema:
        """
        Register new schema
        
        Args:
            schema_id: Schema ID
            name: Schema name
            namespace: Schema namespace
            resource_type: Resource type
            cloud: Cloud provider
            description: Schema description
            owner: Schema owner
            schema_definition: Schema definition
            format: Schema format
            compatibility_rules: Compatibility rules
            tags: Schema tags
            
        Returns:
            Schema
        """
        logger.info(f"Registering schema: {schema_id}")
        
        if schema_id in self.schemas:
            raise ValueError(f"Schema already exists: {schema_id}")
        
        # Create schema version
        version_id = f"{schema_id}-v1"
        version = SchemaVersion(
            version_id=version_id,
            schema_id=schema_id,
            version_number=1,
            schema_definition=schema_definition,
            format=format,
            created_at=datetime.utcnow(),
            created_by=owner,
            description=description,
            compatibility_rules=compatibility_rules or {
                "backward": True,
                "forward": False,
                "full": False
            }
        )
        
        # Create schema
        schema = Schema(
            schema_id=schema_id,
            name=name,
            namespace=namespace,
            resource_type=resource_type,
            cloud=cloud,
            description=description,
            owner=owner,
            current_version=1,
            versions={1: version},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=tags or {}
        )
        
        self.schemas[schema_id] = schema
        
        logger.info(f"Schema registered: {schema_id}")
        return schema
    
    async def get_schema(self, schema_id: str, version: Optional[int] = None) -> Optional[Schema]:
        """
        Get schema by ID
        
        Args:
            schema_id: Schema ID
            version: Version number (optional, latest if not specified)
            
        Returns:
            Schema if found, None otherwise
        """
        schema = self.schemas.get(schema_id)
        
        if schema and version:
            # Verify version exists
            if version not in schema.versions:
                return None
        
        return schema
    
    async def update_schema(
        self,
        schema_id: str,
        schema_definition: Dict[str, Any],
        description: str,
        updated_by: str,
        compatibility_rules: Optional[Dict[str, Any]] = None
    ) -> Optional[Schema]:
        """
        Update schema with new version
        
        Args:
            schema_id: Schema ID
            schema_definition: New schema definition
            description: Update description
            updated_by: User who updated
            compatibility_rules: Compatibility rules
            
        Returns:
            Updated schema
        """
        schema = self.schemas.get(schema_id)
        if not schema:
            logger.warning(f"Schema not found: {schema_id}")
            return None
        
        # Check compatibility
        current_version = schema.versions[schema.current_version]
        is_compatible = await self._check_compatibility(
            current_version.schema_definition,
            schema_definition,
            current_version.compatibility_rules
        )
        
        if not is_compatible:
            raise ValueError("Schema update violates compatibility rules")
        
        # Create new version
        new_version_number = schema.current_version + 1
        version_id = f"{schema_id}-v{new_version_number}"
        
        version = SchemaVersion(
            version_id=version_id,
            schema_id=schema_id,
            version_number=new_version_number,
            schema_definition=schema_definition,
            format=current_version.format,
            created_at=datetime.utcnow(),
            created_by=updated_by,
            description=description,
            compatibility_rules=compatibility_rules or current_version.compatibility_rules
        )
        
        # Add version
        schema.versions[new_version_number] = version
        schema.current_version = new_version_number
        schema.updated_at = datetime.utcnow()
        
        logger.info(f"Schema updated: {schema_id} to v{new_version_number}")
        return schema
    
    async def _check_compatibility(
        self,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> bool:
        """
        Check schema compatibility
        
        Args:
            old_schema: Old schema
            new_schema: New schema
            rules: Compatibility rules
            
        Returns:
            True if compatible, False otherwise
        """
        # Simplified compatibility check
        # In real implementation, use proper schema comparison
        
        if rules.get("full", False):
            # Full compatibility: schemas must be identical
            return old_schema == new_schema
        
        if rules.get("backward", False):
            # Backward compatibility: new schema can read old data
            # Simplified: check if required fields exist
            old_fields = set(old_schema.get("fields", []))
            new_fields = set(new_schema.get("fields", []))
            return old_fields.issubset(new_fields)
        
        if rules.get("forward", False):
            # Forward compatibility: old schema can read new data
            new_fields = set(new_schema.get("fields", []))
            old_fields = set(old_schema.get("fields", []))
            return new_fields.issubset(old_fields)
        
        return True
    
    async def get_schema_version(
        self,
        schema_id: str,
        version: int
    ) -> Optional[SchemaVersion]:
        """
        Get specific schema version
        
        Args:
            schema_id: Schema ID
            version: Version number
            
        Returns:
            Schema version if found, None otherwise
        """
        schema = self.schemas.get(schema_id)
        if not schema:
            return None
        
        return schema.versions.get(version)
    
    async def list_schemas(
        self,
        resource_type: Optional[str] = None,
        cloud: Optional[str] = None,
        owner: Optional[str] = None,
        namespace: Optional[str] = None
    ) -> List[Schema]:
        """
        List schemas
        
        Args:
            resource_type: Resource type filter
            cloud: Cloud provider filter
            owner: Owner filter
            namespace: Namespace filter
            
        Returns:
            List of schemas
        """
        schemas = list(self.schemas.values())
        
        if resource_type:
            schemas = [s for s in schemas if s.resource_type == resource_type]
        
        if cloud:
            schemas = [s for s in schemas if s.cloud == cloud]
        
        if owner:
            schemas = [s for s in schemas if s.owner == owner]
        
        if namespace:
            schemas = [s for s in schemas if s.namespace == namespace]
        
        return schemas
    
    async def search_schemas(
        self,
        query: str,
        limit: int = 100
    ) -> List[Schema]:
        """
        Search schemas
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching schemas
        """
        query_lower = query.lower()
        
        results = []
        for schema in self.schemas.values():
            # Search in name, description, namespace
            if (query_lower in schema.name.lower() or
                query_lower in schema.description.lower() or
                query_lower in schema.namespace.lower()):
                results.append(schema)
        
        return results[:limit]
    
    async def validate_schema(
        self,
        schema_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate data against schema
        
        Args:
            schema_id: Schema ID
            data: Data to validate
            
        Returns:
            Validation result
        """
        schema = self.schemas.get(schema_id)
        if not schema:
            return {"valid": False, "errors": ["Schema not found"]}
        
        # Get latest version
        version = schema.versions[schema.current_version]
        schema_def = version.schema_definition
        
        # Simplified validation
        errors = []
        
        # Check required fields
        required_fields = schema_def.get("required", [])
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check field types
        fields = schema_def.get("fields", [])
        for field in fields:
            field_name = field.get("name")
            field_type = field.get("type")
            
            if field_name in data:
                value = data[field_name]
                if not self._validate_type(value, field_type):
                    errors.append(
                        f"Field {field_name} has invalid type: "
                        f"expected {field_type}, got {type(value).__name__}"
                    )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "schema_id": schema_id,
            "version": schema.current_version
        }
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        Validate value type
        
        Args:
            value: Value to check
            expected_type: Expected type
            
        Returns:
            True if valid, False otherwise
        """
        type_mapping = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
            "array": list,
            "object": dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if not expected_python_type:
            return True  # Unknown type, assume valid
        
        return isinstance(value, expected_python_type)
    
    async def get_schema_versions(
        self,
        schema_id: str
    ) -> List[SchemaVersion]:
        """
        Get all versions of schema
        
        Args:
            schema_id: Schema ID
            
        Returns:
            List of schema versions
        """
        schema = self.schemas.get(schema_id)
        if not schema:
            return []
        
        return list(schema.versions.values())
    
    async def delete_schema(self, schema_id: str) -> bool:
        """
        Delete schema
        
        Args:
            schema_id: Schema ID
            
        Returns:
            True if deleted, False otherwise
        """
        if schema_id in self.schemas:
            del self.schemas[schema_id]
            logger.info(f"Schema deleted: {schema_id}")
            return True
        
        logger.warning(f"Schema not found: {schema_id}")
        return False
    
    async def get_registry_analytics(self) -> Dict[str, Any]:
        """
        Get registry analytics
        
        Returns:
            Registry statistics
        """
        total_schemas = len(self.schemas)
        
        # By resource type
        by_resource_type = {}
        for schema in self.schemas.values():
            resource_type = schema.resource_type
            by_resource_type[resource_type] = by_resource_type.get(resource_type, 0) + 1
        
        # By cloud
        by_cloud = {}
        for schema in self.schemas.values():
            cloud = schema.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # By format
        by_format = {}
        for schema in self.schemas.values():
            latest_version = schema.versions[schema.current_version]
            format_value = latest_version.format.value
            by_format[format_value] = by_format.get(format_value, 0) + 1
        
        # By owner
        by_owner = {}
        for schema in self.schemas.values():
            owner = schema.owner
            by_owner[owner] = by_owner.get(owner, 0) + 1
        
        return {
            "total_schemas": total_schemas,
            "by_resource_type": by_resource_type,
            "by_cloud": by_cloud,
            "by_format": by_format,
            "by_owner": by_owner
        }