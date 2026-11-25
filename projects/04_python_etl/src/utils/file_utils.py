"""
File system utility functions for enterprise ETL pipelines.

Provides file validation, atomic directory creation, checksum calculations,
and safe JSON serialization.
"""

import hashlib
import json
import os
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, Union

logger = logging.getLogger("etl_pipeline.utils.file")


class FileOperationError(Exception):
    """Custom exception for file manipulation operations."""
    pass


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure that a directory exists, creating it and parent directories if missing.

    Args:
        path: Path to directory or file location.

    Returns:
        Path: Resolved Path object for the directory.

    Raises:
        FileOperationError: If directory creation fails.
    """
    try:
        dir_path = Path(path)
        if dir_path.suffix:  # If path includes a filename extension, take parent
            dir_path = dir_path.parent
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory existence: {dir_path}")
        return dir_path
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {str(e)}")
        raise FileOperationError(f"Directory creation failed for '{path}': {str(e)}") from e


def compute_file_hash(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Compute cryptographic checksum hash of a file for data integrity verification.

    Args:
        file_path: Path to the target file.
        algorithm: Hashing algorithm (sha256, md5, sha1).

    Returns:
        str: Hexadecimal digest string.

    Raises:
        FileOperationError: If file read or hashing fails.
    """
    target = Path(file_path)
    if not target.exists():
        raise FileOperationError(f"File not found for hash calculation: {file_path}")

    try:
        hasher = hashlib.new(algorithm)
        with open(target, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        logger.debug(f"Computed {algorithm} hash for {file_path}: {digest[:8]}...")
        return digest
    except Exception as e:
        logger.error(f"Error computing hash for {file_path}: {str(e)}")
        raise FileOperationError(f"Failed to hash file '{file_path}': {str(e)}") from e


def safe_write_json(data: Any, target_path: Union[str, Path], indent: int = 2) -> Path:
    """
    Atomically write python data structure to JSON using a temporary file.

    Args:
        data: Serializable Python object.
        target_path: Target path for output file.
        indent: JSON indentation spaces.

    Returns:
        Path: Path to written JSON file.

    Raises:
        FileOperationError: If writing or serialization fails.
    """
    target = Path(target_path)
    ensure_directory(target)
    temp_path = target.with_suffix(".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str)
        
        # Atomic rename
        shutil.move(str(temp_path), str(target))
        logger.info(f"Successfully wrote JSON payload to {target}")
        return target
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        logger.error(f"Failed writing JSON to {target}: {str(e)}")
        raise FileOperationError(f"Failed to write JSON to '{target}': {str(e)}") from e
