"""Shared dependencies for API endpoints."""

from typing import Annotated

from fastapi import Depends

from src.config import Settings, get_settings
from src.storage.sqlite import SQLiteStorage


def get_storage(settings: Annotated[Settings, Depends(get_settings)]) -> SQLiteStorage:
    """Get SQLite storage instance.

    This is a dependency that provides a configured SQLiteStorage instance
    to endpoints that need to access stored connections and metadata.
    """
    return SQLiteStorage(settings.db_path)


# Type aliases for cleaner endpoint signatures
StorageDep = Annotated[SQLiteStorage, Depends(get_storage)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
