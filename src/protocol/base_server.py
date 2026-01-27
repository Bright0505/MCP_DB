"""Base MCP server - Transport-agnostic MCP protocol implementation.

This module provides the core MCP server functionality independent of transport mechanism.
Future refactoring will extract common MCP logic from server.py and http_server.py here.
"""

import logging
from typing import Optional
from mcp.server import Server
from database.manager import DatabaseManager
from tools import get_all_tools
from tools.handlers import handle_tool_call

logger = logging.getLogger(__name__)


class BaseMCPServer:
    """Base MCP server providing core protocol functionality.

    This class encapsulates the MCP protocol logic independent of
    the transport mechanism (STDIO, HTTP/SSE, etc.).
    """

    def __init__(self, db_manager: DatabaseManager, server_name: str = None):
        """Initialize base MCP server.

        Args:
            db_manager: DatabaseManager instance for database operations
            server_name: Name of the MCP server
        """
        import os
        self.db_manager = db_manager
        if server_name is None:
            server_name = os.getenv("MCP_SERVER_NAME", "mcp-db")
        self.server = Server(server_name)
        self._setup_handlers()
        logger.info(f"Initialized {server_name} MCP server")

    def _setup_handlers(self):
        """Setup MCP protocol handlers."""

        @self.server.list_tools()
        async def list_tools():
            """List all available tools."""
            return get_all_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            """Handle tool execution."""
            # Create CallToolRequest-like object from parameters
            # Note: We use a simple object instead of mcp.types.CallToolRequest
            # because the MCP library provides name/arguments directly
            request = type('CallToolRequest', (), {
                'name': name,
                'arguments': arguments or {}
            })()
            return await handle_tool_call(request, self.db_manager)

        @self.server.list_prompts()
        async def list_prompts():
            """List available prompts (currently none)."""
            return []

        @self.server.list_resources()
        async def list_resources():
            """List available resources (currently none)."""
            return []
