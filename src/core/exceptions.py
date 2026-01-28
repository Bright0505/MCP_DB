"""Custom exceptions for MCP Multi-Database Connector."""


class MCPDBError(Exception):
    """Base exception for all MCP database connector errors."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }



class ToolExecutionError(MCPDBError):
    """Exception raised when tool execution fails."""
    pass


class SchemaLoadError(MCPDBError):
    """Exception raised when schema loading fails."""
    pass


class DatabaseConnectionError(MCPDBError):
    """Exception raised when database connection fails."""
    pass


class ConfigurationError(MCPDBError):
    """Exception raised when configuration is invalid."""
    pass


class QueryExecutionError(MCPDBError):
    """Exception raised when query execution fails."""
    pass


class CacheError(MCPDBError):
    """Exception raised when cache operations fail."""
    pass
