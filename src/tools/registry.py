"""Tool registry for routing MCP tool calls to handlers."""

import logging
from typing import Dict, Any
from mcp.types import CallToolRequest

from tools.base import ToolHandler
from tools.handlers import (
    QueryHandler,
    ConnectionHandler,
    DependencyHandler,
    SchemaHandler,
    CacheHandler,
    ExportHandler,
    SyntaxHandler,
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for MCP tool handlers.

    Routes tool calls to appropriate handlers based on tool name.
    """

    def __init__(self):
        self.handlers: Dict[str, ToolHandler] = {}
        self._register_handlers()

    def _register_handlers(self):
        """Register all tool handlers."""
        # Create all handler instances
        handler_classes = [
            QueryHandler,
            ConnectionHandler,
            DependencyHandler,
            SchemaHandler,
            CacheHandler,
            ExportHandler,
            SyntaxHandler,
        ]

        # Register each handler's tools
        for handler_class in handler_classes:
            handler = handler_class()
            for tool_name in handler.tool_names:
                self.handlers[tool_name] = handler
                logger.debug(f"Registered {tool_name} -> {handler_class.__name__}")

        logger.info(f"✅ Registered {len(self.handlers)} MCP tools across {len(handler_classes)} handlers")

    async def handle_tool(
        self,
        request: CallToolRequest,
        db_manager: Any
    ) -> Dict[str, Any]:
        """
        Route tool call to appropriate handler.

        Args:
            request: MCP tool call request
            db_manager: Database manager instance

        Returns:
            Tool execution result or error message
        """
        handler = self.handlers.get(request.name)

        if handler:
            # Use registered handler
            logger.debug(f"Routing {request.name} to {handler.__class__.__name__}")
            return await handler.handle(request, db_manager)
        else:
            # Tool not yet migrated to handler system
            # Return None to signal fallback to legacy handling
            return None

    def is_tool_registered(self, tool_name: str) -> bool:
        """Check if a tool has a registered handler."""
        return tool_name in self.handlers
