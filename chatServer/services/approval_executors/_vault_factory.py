"""Shared VaultService factory for approval executors."""

from chatServer.config.paths import get_data_dir


def create_vault_service():
    """Create a VaultService instance with no storage sync.

    Used by executors that only need local filesystem access.
    Factored out to avoid duplication across executor modules.
    """
    from chatServer.services.vault_service import VaultService

    return VaultService(storage_sync=None, data_dir=get_data_dir())
