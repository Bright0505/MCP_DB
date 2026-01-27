"""Dependency injection and singleton management for MCP Multi-Database Connector."""

from functools import lru_cache
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)

# Global singletons
_app_config: Optional["AppConfig"] = None
_database_manager: Optional["DatabaseManager"] = None


@lru_cache()
def get_app_config() -> "AppConfig":
    """Get singleton AppConfig instance.

    This function is cached to ensure only one AppConfig instance exists.
    """
    global _app_config
    if _app_config is None:
        from core.config import AppConfig
        _app_config = AppConfig.from_env()
        logger.info("Initialized AppConfig singleton")
    return _app_config


@lru_cache()
def get_database_config() -> "DatabaseConfig":
    """Get singleton DatabaseConfig instance."""
    from core.config import DatabaseConfig
    config = DatabaseConfig.from_env()
    logger.info(f"Loaded DatabaseConfig: {config.db_type} @ {config.server}")
    return config


def get_database_manager(
    config: Optional["DatabaseConfig"] = None,
    app_config: Optional["AppConfig"] = None
) -> "DatabaseManager":
    """Get singleton DatabaseManager instance.

    Args:
        config: Optional DatabaseConfig. If None, uses get_database_config()
        app_config: Optional AppConfig. If None, uses get_app_config()

    Returns:
        DatabaseManager instance (singleton)
    """
    global _database_manager

    if _database_manager is None:
        from database.manager import DatabaseManager

        db_config = config if config is not None else get_database_config()
        app_cfg = app_config if app_config is not None else get_app_config()

        _database_manager = DatabaseManager(db_config, app_cfg)
        logger.info("Initialized DatabaseManager singleton")

    return _database_manager


def reset_singletons():
    """Reset all singletons (useful for testing)."""
    global _app_config, _database_manager
    _app_config = None
    _database_manager = None
    get_app_config.cache_clear()
    get_database_config.cache_clear()
    logger.info("Reset all singletons")


# FastAPI Dependency Injection helpers
def get_db_manager_dependency() -> Generator["DatabaseManager", None, None]:
    """FastAPI dependency for DatabaseManager.

    Usage:
        @router.get("/endpoint")
        async def endpoint(db: DatabaseManager = Depends(get_db_manager_dependency)):
            ...
    """
    db = get_database_manager()
    try:
        yield db
    finally:
        # Cleanup if needed (e.g., close connections)
        pass
