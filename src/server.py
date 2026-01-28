"""MCP server implementation for Multi-Database Connector."""

import asyncio
import logging
import os
from typing import List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    Tool,
    Prompt,
    Resource
)

from database.async_manager import HybridDatabaseManager
from tools.registry import ToolRegistry
from tools.definitions import DB_TOOLS as TOOLS_DEFINITIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global database manager (Hybrid: supports both sync and async)
db_manager: Optional[HybridDatabaseManager] = None

# Global tool registry for modular tool handlers
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def get_db_manager() -> HybridDatabaseManager:
    """Get or create hybrid database manager instance with preload support."""
    global db_manager
    if db_manager is None:
        db_manager = HybridDatabaseManager.create_with_preload()
        logger.info("Hybrid database manager initialized (sync + async support)")
    return db_manager


async def handle_call_tool(
    request: CallToolRequest,
    db_manager: Optional[HybridDatabaseManager] = None
) -> dict:
    """Handle MCP tool calls via the tool registry."""
    try:
        db = db_manager if db_manager is not None else get_db_manager()
        registry = get_tool_registry()

        result = await registry.handle_tool(request, db)
        if result is not None:
            return result

        return {
            "content": [{"type": "text", "text": f"Unknown tool: {request.name}"}]
        }

    except Exception as e:
        logger.error(f"Tool call error in {request.name}: {e}", exc_info=True)
        return {
            "content": [{"type": "text", "text": f"Internal server error in tool '{request.name}': {e}"}]
        }


async def main():
    """Main server entry point."""
    server_name = os.getenv("MCP_SERVER_NAME", "mcp-db")
    server = Server(server_name)

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return TOOLS_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: Optional[dict] = None) -> dict:
        request = type('CallToolRequest', (), {
            'name': name,
            'arguments': arguments or {}
        })()
        return await handle_call_tool(request)

    @server.list_prompts()
    async def list_prompts() -> List[Prompt]:
        return []

    @server.list_resources()
    async def list_resources() -> List[Resource]:
        return []

    logger.info(f"Starting MCP Database Server ({server_name})...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
