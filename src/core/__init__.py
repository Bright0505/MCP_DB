"""Core modules for MCP Multi-Database Connector."""

from .exceptions import (
    MCPDBError,
    ToolExecutionError,
    SchemaLoadError,
    DatabaseConnectionError,
    ConfigurationError
)

__all__ = [
    "MCPDBError",
    "ToolExecutionError",
    "SchemaLoadError",
    "DatabaseConnectionError",
    "ConfigurationError"
]
