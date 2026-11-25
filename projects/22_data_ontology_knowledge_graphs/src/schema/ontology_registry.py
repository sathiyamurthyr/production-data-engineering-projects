"""Ontology schema registry, validator, and backward-compatibility checker."""

from pathlib import Path
from typing import Any, Dict, List, Set
import yaml

from src.models import ClassSpec, PropertySpec, RelationshipSpec


class OntologyValidationError(ValueError):
    """Raised when an instance or link violates the ontology schema."""


class OntologyRegistry:
    """Manages Object Types, Link Types, inheritance, and schema governance."""

    def __init__(
        self,
        version: str,
        namespace: str,
        classes: Dict[str, ClassSpec],
        relationships: Dict[str, RelationshipSpec],
    ) -> None:
        self.version = version
        self.namespace = namespace
        self.classes = classes
        self.relationships = relationships
        self._validate_schema_integrity()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "OntologyRegistry":
        with Path(path).open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OntologyRegistry":
        classes: Dict[str, ClassSpec] = {}
        for cname, cdata in raw.get("classes", {}).items():
            props: Dict[str, PropertySpec] = {}
            for pname, pdata in cdata.get("properties", {}).items():
                props[pname] = PropertySpec(
                    name=pname,
                    data_type=str(pdata.get("type", "string")),
                    required=bool(pdata.get("required", False)),
                    allowed_values=pdata.get("allowed_values"),
                    default=pdata.get("default"),
                )
            classes[cname] = ClassSpec(
                name=cname,
                description=str(cdata.get("description", "")),
                primary_key=str(cdata.get("primary_key", "id")),
                parent=cdata.get("parent"),
                abstract=bool(cdata.get("abstract", False)),
                properties=props,
            )

        relationships: Dict[str, RelationshipSpec] = {}
        for rname, rdata in raw.get("relationships", {}).items():
            relationships[rname] = RelationshipSpec(
                name=rname,
                domain=str(rdata["domain"]),
                range=str(rdata["range"]),
                cardinality=str(rdata.get("cardinality", "N:M")),
                inverse=rdata.get("inverse"),
                transitive=bool(rdata.get("transitive", False)),
                description=str(rdata.get("description", "")),
            )

        return cls(
            version=str(raw.get("version", "1.0.0")),
            namespace=str(raw.get("namespace", "urn:de:ontology:")),
            classes=classes,
            relationships=relationships,
        )

    def _validate_schema_integrity(self) -> None:
        for cname, cspec in self.classes.items():
            seen: Set[str] = {cname}
            curr = cspec.parent
            while curr is not None:
                if curr not in self.classes:
                    raise OntologyValidationError(
                        f"Class '{cname}' references unknown parent '{curr}'"
                    )
                if curr in seen:
                    raise OntologyValidationError(f"Inheritance cycle detected at '{cname}'")
                seen.add(curr)
                curr = self.classes[curr].parent

        for rname, rspec in self.relationships.items():
            if rspec.domain not in self.classes:
                raise OntologyValidationError(
                    f"Relationship '{rname}' has unknown domain '{rspec.domain}'"
                )
            if rspec.range not in self.classes:
                raise OntologyValidationError(
                    f"Relationship '{rname}' has unknown range '{rspec.range}'"
                )

    def is_subclass_of(self, child_class: str, parent_class: str) -> bool:
        """Return True if child_class equals or inherits from parent_class."""
        if child_class not in self.classes or parent_class not in self.classes:
            return False
        curr: str | None = child_class
        while curr is not None:
            if curr == parent_class:
                return True
            curr = self.classes[curr].parent
        return False

    def get_subclasses(self, parent_class: str, include_self: bool = True) -> List[str]:
        """Return all concrete and abstract subclasses of parent_class."""
        return [
            cname
            for cname in self.classes
            if (include_self or cname != parent_class) and self.is_subclass_of(cname, parent_class)
        ]

    def get_effective_properties(self, class_name: str) -> Dict[str, PropertySpec]:
        """Merge inherited parent properties with child overrides."""
        if class_name not in self.classes:
            raise OntologyValidationError(f"Unknown class '{class_name}'")
        lineage: List[ClassSpec] = []
        curr: str | None = class_name
        while curr is not None:
            lineage.append(self.classes[curr])
            curr = self.classes[curr].parent
        merged: Dict[str, PropertySpec] = {}
        for spec in reversed(lineage):
            merged.update(spec.properties)
        return merged

    def make_uri(self, class_name: str, pk_value: str) -> str:
        """Build a canonical URN/URI for an ontology instance."""
        return f"{self.namespace}{class_name.lower()}:{pk_value}"

    def validate_instance(self, class_name: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Validate properties against class schema, applying defaults and rejecting invalid values."""
        if class_name not in self.classes:
            raise OntologyValidationError(f"Unknown ontology class: '{class_name}'")
        cspec = self.classes[class_name]
        if cspec.abstract:
            raise OntologyValidationError(f"Cannot instantiate abstract class '{class_name}'")

        effective = self.get_effective_properties(class_name)
        normalized = dict(properties)

        for prop_name, pspec in effective.items():
            if prop_name not in normalized or normalized[prop_name] is None:
                if pspec.default is not None:
                    normalized[prop_name] = pspec.default
                elif pspec.required:
                    raise OntologyValidationError(
                        f"Missing required property '{prop_name}' for class '{class_name}'"
                    )
                continue

            val = normalized[prop_name]
            self._check_type(class_name, prop_name, val, pspec.data_type)
            if pspec.allowed_values is not None and val not in pspec.allowed_values:
                raise OntologyValidationError(
                    f"Invalid value '{val}' for {class_name}.{prop_name}; "
                    f"allowed={pspec.allowed_values}"
                )

        return normalized

    def validate_relationship(
        self, predicate: str, subject_class: str, object_class: str
    ) -> RelationshipSpec:
        """Verify predicate exists and subject/object satisfy domain/range inheritance."""
        if predicate not in self.relationships:
            raise OntologyValidationError(f"Unknown relationship predicate: '{predicate}'")
        rspec = self.relationships[predicate]
        if not self.is_subclass_of(subject_class, rspec.domain):
            raise OntologyValidationError(
                f"Subject class '{subject_class}' is not compatible with domain '{rspec.domain}' "
                f"for '{predicate}'"
            )
        if not self.is_subclass_of(object_class, rspec.range):
            raise OntologyValidationError(
                f"Object class '{object_class}' is not compatible with range '{rspec.range}' "
                f"for '{predicate}'"
            )
        return rspec

    @staticmethod
    def _check_type(class_name: str, prop_name: str, value: Any, expected: str) -> None:
        if expected == "string" and not isinstance(value, str):
            raise OntologyValidationError(f"{class_name}.{prop_name} must be string")
        if expected == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise OntologyValidationError(f"{class_name}.{prop_name} must be number")
        if expected == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            raise OntologyValidationError(f"{class_name}.{prop_name} must be integer")
        if expected == "boolean" and not isinstance(value, bool):
            raise OntologyValidationError(f"{class_name}.{prop_name} must be boolean")


def check_backward_compatibility(
    previous: OntologyRegistry, current: OntologyRegistry
) -> List[str]:
    """Detect breaking schema changes between two ontology versions."""
    breaking: List[str] = []

    for cname, old_class in previous.classes.items():
        if cname not in current.classes:
            breaking.append(f"Removed class '{cname}'")
            continue
        old_props = previous.get_effective_properties(cname)
        new_props = current.get_effective_properties(cname)
        for pname, old_prop in old_props.items():
            if pname not in new_props:
                breaking.append(f"Removed property '{cname}.{pname}'")
            elif new_props[pname].data_type != old_prop.data_type:
                breaking.append(
                    f"Changed type of '{cname}.{pname}' from {old_prop.data_type} "
                    f"to {new_props[pname].data_type}"
                )
        for pname, new_prop in new_props.items():
            if pname not in old_props and new_prop.required and new_prop.default is None:
                breaking.append(
                    f"Added required property '{cname}.{pname}' without default"
                )

    for rname, old_rel in previous.relationships.items():
        if rname not in current.relationships:
            breaking.append(f"Removed relationship '{rname}'")
        else:
            new_rel = current.relationships[rname]
            if new_rel.domain != old_rel.domain or new_rel.range != old_rel.range:
                breaking.append(
                    f"Changed domain/range of relationship '{rname}' "
                    f"({old_rel.domain}->{old_rel.range} vs {new_rel.domain}->{new_rel.range})"
                )

    return breaking
