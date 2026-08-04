"""Data Mesh Contract Versioning."""

from dataclasses import dataclass
from typing import NamedTuple


class VersionParts(NamedTuple):
    """Semantic version parts."""

    major: int
    minor: int
    patch: int


@dataclass
class SemanticVersion:
    """Semantic versioning for data contracts."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        """Parse version string like '1.2.3'."""
        parts = version_str.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version_str}")
        return cls(
            major=int(parts[0]),
            minor=int(parts[1]),
            patch=int(parts[2]),
        )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: "SemanticVersion") -> bool:
        """Check backward compatibility (major version must match)."""
        return self.major == other.major


class VersionManager:
    """Manages contract versions."""

    def __init__(self):
        self._versions: dict[str, list[SemanticVersion]] = {}

    def register_version(self, product: str, version: SemanticVersion) -> None:
        """Register a new version of a product."""
        if product not in self._versions:
            self._versions[product] = []
        if version not in self._versions[product]:
            self._versions[product].append(version)

    def get_latest_version(self, product: str) -> SemanticVersion | None:
        """Get the latest version of a product."""
        versions = self._versions.get(product, [])
        if not versions:
            return None
        return max(versions, key=lambda v: (v.major, v.minor, v.patch))

    def check_compatibility(
        self,
        product: str,
        consumer_version: SemanticVersion,
    ) -> bool:
        """Check if latest version is compatible with consumer."""
        latest = self.get_latest_version(product)
        if not latest:
            return False
        return latest.is_compatible_with(consumer_version)