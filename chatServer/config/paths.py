"""Shared path utilities."""

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Return the sandbox data directory (default ``/data``)."""
    return Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
