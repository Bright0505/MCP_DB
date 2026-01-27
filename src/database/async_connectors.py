"""Async database connectors with connection pooling."""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
import logging
import os

try:
    import aioodbc
except ImportError:
    aioodbc = None

try:
    import asyncpg
except ImportError:
    asyncpg = None

from core.config import DatabaseConfig

logger = logging.getLogger(__name__)


class AsyncDatabaseConnector(ABC):
    """Abstract base class for async database connectors."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool = None

    @abstractmethod
    async def initialize_pool(self, pool_size: int = 10):
        """Initialize connection pool."""
        pass

    @abstractmethod
    @asynccontextmanager
    async def get_connection(self):
        """Get async database connection from pool."""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: Optional[List] = None) -> Dict[str, Any]:
        """Execute async SELECT query and return results."""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test async database connection."""
        pass

    @abstractmethod
    async def close(self):
        """Close connection pool."""
        pass


class AsyncMSSQLConnector(AsyncDatabaseConnector):
    """Async SQL Server connector using aioodbc with connection pooling."""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        if aioodbc is None:
            raise ImportError("aioodbc is required for async SQL Server connections")
        self.connection_string = config.get_connection_string()

    async def initialize_pool(self, pool_size: int = 10):
        """Initialize aioodbc connection pool."""
        try:
            self._pool = await aioodbc.create_pool(
                dsn=self.connection_string,
                minsize=2,
                maxsize=pool_size,
                autocommit=True,
                timeout=self.config.command_timeout
            )
            logger.info(f"✅ Async MSSQL connection pool initialized (size: {pool_size})")
        except Exception as e:
            logger.error(f"Failed to initialize async MSSQL pool: {e}")
            raise

    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool."""
        if not self._pool:
            await self.initialize_pool()

        async with self._pool.acquire() as conn:
            yield conn

    async def execute_query(self, query: str, params: Optional[List] = None) -> Dict[str, Any]:
        """Execute async SELECT query."""
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or [])

                    # Get column names
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []

                    # Fetch all rows
                    rows = await cursor.fetchall()

                    # Convert to dict list
                    results = [dict(zip(columns, row)) for row in rows]

                    return {
                        "success": True,
                        "results": results,
                        "row_count": len(results),
                        "columns": columns
                    }

        except Exception as e:
            logger.error(f"Async query error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Query execution failed: {str(e)}",
                "query": query[:200]  # Log first 200 chars for debugging
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Test async SQL Server connection."""
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT @@VERSION")
                    row = await cursor.fetchone()
                    version = row[0] if row else "Unknown"

                    return {
                        "success": True,
                        "message": "Async connection successful",
                        "server_info": {
                            "server_version": version,
                            "database": self.config.database,
                            "server": self.config.server,
                            "port": self.config.port,
                            "driver": self.config.driver,
                            "encrypt": self.config.encrypt,
                            "current_database": self.config.database,
                            "connected": True
                        }
                    }
        except Exception as e:
            logger.error(f"Async SQL Server connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Connection test failed: {str(e)}",
                "connection_info": {
                    "server": self.config.server,
                    "database": self.config.database,
                    "port": self.config.port,
                    "driver": self.config.driver,
                    "encrypt": self.config.encrypt
                }
            }

    async def close(self):
        """Close connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            logger.info("Async MSSQL connection pool closed")


class AsyncPostgreSQLConnector(AsyncDatabaseConnector):
    """Async PostgreSQL connector using asyncpg with connection pooling."""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        if asyncpg is None:
            raise ImportError("asyncpg is required for async PostgreSQL connections")

    async def initialize_pool(self, pool_size: int = 10):
        """Initialize asyncpg connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                host=self.config.server,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                port=self.config.port or 5432,
                min_size=2,
                max_size=pool_size,
                command_timeout=self.config.command_timeout
            )
            logger.info(f"✅ Async PostgreSQL connection pool initialized (size: {pool_size})")
        except Exception as e:
            logger.error(f"Failed to initialize async PostgreSQL pool: {e}")
            raise

    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool."""
        if not self._pool:
            await self.initialize_pool()

        async with self._pool.acquire() as conn:
            yield conn

    async def execute_query(self, query: str, params: Optional[List] = None) -> Dict[str, Any]:
        """Execute async SELECT query."""
        try:
            async with self.get_connection() as conn:
                # asyncpg returns Record objects
                rows = await conn.fetch(query, *(params or []))

                if rows:
                    columns = list(rows[0].keys())
                    results = [dict(row) for row in rows]
                else:
                    columns = []
                    results = []

                return {
                    "success": True,
                    "results": results,
                    "row_count": len(results),
                    "columns": columns
                }

        except Exception as e:
            logger.error(f"Async query error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Query execution failed: {str(e)}",
                "query": query[:200]
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Test async PostgreSQL connection."""
        try:
            async with self.get_connection() as conn:
                version = await conn.fetchval("SELECT version()")

                return {
                    "success": True,
                    "message": "Async connection successful",
                    "server_info": {
                        "server_version": version,
                        "database": self.config.database,
                        "server": self.config.server,
                        "port": self.config.port or 5432,
                        "current_database": self.config.database,
                        "connected": True
                    }
                }
        except Exception as e:
            logger.error(f"Async PostgreSQL connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Connection test failed: {str(e)}",
                "connection_info": {
                    "server": self.config.server,
                    "database": self.config.database,
                    "port": self.config.port or 5432
                }
            }

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Async PostgreSQL connection pool closed")


def create_async_database_connector(config: DatabaseConfig) -> AsyncDatabaseConnector:
    """
    Factory function to create async database connector based on config.

    Args:
        config: Database configuration

    Returns:
        AsyncDatabaseConnector instance

    Raises:
        ValueError: If database type is not supported
    """
    db_type = config.db_type.lower()

    if db_type == "postgresql":
        return AsyncPostgreSQLConnector(config)
    elif db_type == "mssql":
        return AsyncMSSQLConnector(config)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
