"""Database connectors for different database types."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Generator
from contextlib import contextmanager
import logging

try:
    import pyodbc
except ImportError:
    pyodbc = None

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

from core.config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseConnector(ABC):
    """Abstract base class for database connectors."""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection and return status."""
        pass

    @abstractmethod
    @contextmanager
    def get_connection(self):
        """Get database connection context manager."""
        pass

    @abstractmethod
    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute SELECT query and return results."""
        pass

    @abstractmethod
    def execute_command(self, command: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute INSERT/UPDATE/DELETE command and return result."""
        pass


class MSSQLConnector(DatabaseConnector):
    """SQL Server database connector using pyodbc."""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        if pyodbc is None:
            raise ImportError("pyodbc is required for SQL Server connections")
        self.connection_string = config.get_connection_string()

    def test_connection(self) -> Dict[str, Any]:
        """Test SQL Server connection."""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                return {
                    "success": True,
                    "message": "Connection successful",
                    "server_info": {
                        "version": version,
                        "database": self.config.database,
                        "server": self.config.server
                    }
                }
        except Exception as e:
            logger.error(f"SQL Server connection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "connection_string": self.connection_string.replace(
                    self.config.password or "", "***" if self.config.password else ""
                )
            }

    @contextmanager
    def get_connection(self):
        """Get SQL Server connection context manager."""
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute SELECT query on SQL Server."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # Get column names
                columns = [column[0] for column in cursor.description] if cursor.description else []

                # Fetch all results
                results = cursor.fetchall()

                # Convert to list of dictionaries
                data = []
                for row in results:
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[columns[i]] = value
                    data.append(row_dict)

                return {
                    "success": True,
                    "results": data,
                    "row_count": len(data),
                    "columns": columns
                }
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    def execute_command(self, command: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute INSERT/UPDATE/DELETE command on SQL Server."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if params:
                    cursor.execute(command, params)
                else:
                    cursor.execute(command)

                rows_affected = cursor.rowcount
                conn.commit()

                return {
                    "success": True,
                    "rows_affected": rows_affected,
                    "message": f"Command executed successfully. {rows_affected} rows affected."
                }
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }


class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL database connector using psycopg2."""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        if psycopg2 is None:
            raise ImportError("psycopg2 is required for PostgreSQL connections")
        self.connection_string = config.get_connection_string()

    def test_connection(self) -> Dict[str, Any]:
        """Test PostgreSQL connection."""
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    return {
                        "success": True,
                        "message": "Connection successful",
                        "server_info": {
                            "version": version,
                            "database": self.config.database,
                            "server": self.config.server,
                            "schema": self.config.schema
                        }
                    }
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "connection_string": self.connection_string.replace(
                    self.config.password or "", "***" if self.config.password else ""
                )
            }

    @contextmanager
    def get_connection(self):
        """Get PostgreSQL connection context manager."""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute SELECT query on PostgreSQL."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    # Fetch all results as list of dictionaries
                    results = cursor.fetchall()

                    # Convert RealDictRow to regular dict
                    data = [dict(row) for row in results]

                    # Get column names
                    columns = list(data[0].keys()) if data else []

                    return {
                        "success": True,
                        "results": data,
                        "row_count": len(data),
                        "columns": columns
                    }
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    def execute_command(self, command: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute INSERT/UPDATE/DELETE command on PostgreSQL."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(command, params)
                    else:
                        cursor.execute(command)

                    rows_affected = cursor.rowcount
                    conn.commit()

                    return {
                        "success": True,
                        "rows_affected": rows_affected,
                        "message": f"Command executed successfully. {rows_affected} rows affected."
                    }
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }


def create_database_connector(config: DatabaseConfig) -> DatabaseConnector:
    """Factory function to create appropriate database connector."""
    if config.db_type == "postgresql":
        return PostgreSQLConnector(config)
    elif config.db_type == "mssql":
        return MSSQLConnector(config)
    else:
        raise ValueError(f"Unsupported database type: {config.db_type}")