"""Tool handlers for MCP Multi-Database Connector.

This module provides unified tool execution handlers.
Future refactoring will move handler implementations here from server.py.
"""

from typing import Optional
from mcp.types import CallToolRequest
from database.manager import DatabaseManager

# For now, import from server.py
# TODO: Move handle_call_tool implementation here in future refactoring
from server import handle_call_tool as _handle_call_tool


async def handle_tool_call(
    request: CallToolRequest,
    db_manager: Optional[DatabaseManager] = None
) -> dict:
    """Unified tool handler entry point.

    Args:
        request: The MCP tool call request
        db_manager: Optional DatabaseManager instance

    Returns:
        dict: Tool execution result in MCP format
    """
    return await _handle_call_tool(request, db_manager)


# Alias for backward compatibility
handle_call_tool = handle_tool_call
