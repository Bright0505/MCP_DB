"""Core modules for MCP Multi-Database Connector."""

from .exceptions import (
    MCPDBError,
    MCPPOSDBError,  # backward compatibility alias
    ToolExecutionError,
    SchemaLoadError,
    DatabaseConnectionError,
    ConfigurationError
)

__all__ = [
    "MCPDBError",
    "MCPPOSDBError",
    "ToolExecutionError",
    "SchemaLoadError",
    "DatabaseConnectionError",
    "ConfigurationError"
]
