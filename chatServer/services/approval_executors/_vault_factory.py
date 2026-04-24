"""Shared VaultService factory for approval executors."""

import os
from pathlib import Path


def create_vault_service():
    """Create a VaultService instance with no storage sync.

    Used by executors that only need local filesystem access.
    Factored out to avoid duplication across executor modules.
    """
    from chatServer.services.vault_service import VaultService

    data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
    return VaultService(storage_sync=None, data_dir=data_dir)
