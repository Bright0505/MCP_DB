"""Base classes for MCP tool handlers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from mcp.types import CallToolRequest


class ToolHandler(ABC):
    """Abstract base class for MCP tool handlers."""

    @property
    @abstractmethod
    def tool_names(self) -> List[str]:
        """Return list of tool names this handler supports."""
        pass

    @abstractmethod
    async def handle(self, request: CallToolRequest, db_manager: Any) -> Dict[str, Any]:
        """
        Handle tool invocation.

        Args:
            request: MCP tool call request
            db_manager: Database manager instance

        Returns:
            MCP response dictionary with 'content' key
        """
        pass

    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "content": [{
                "type": "text",
                "text": f"❌ Error: {error_message}"
            }]
        }

    def _success_response(self, text: str) -> Dict[str, Any]:
        """Create standardized success response."""
        return {
            "content": [{
                "type": "text",
                "text": text
            }]
        }
