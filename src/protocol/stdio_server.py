"""STDIO transport MCP server."""

import asyncio
import logging
from typing import Optional
from mcp.server.stdio import stdio_server
from core.config import DatabaseConfig, AppConfig
from database.manager import DatabaseManager
from protocol.base_server import BaseMCPServer

logger = logging.getLogger(__name__)


class StdioMCPServer(BaseMCPServer):
    """MCP server using STDIO transport."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize STDIO MCP server.

        Args:
            db_manager: DatabaseManager instance
        """
        super().__init__(db_manager)

    async def run(self):
        """Run the STDIO MCP server."""
        logger.info("Starting STDIO MCP server")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def run_stdio_server(
    config: Optional[DatabaseConfig] = None,
    app_config: Optional[AppConfig] = None
):
    """Run STDIO MCP server with given configuration.

    Args:
        config: Database configuration (optional, defaults to env)
        app_config: App configuration (optional, defaults to env)
    """
    # Create database manager with preload
    if not config or not app_config:
        db_manager = DatabaseManager.create_with_preload(config, app_config)
    else:
        db_manager = DatabaseManager(config, app_config)

    # Create and run server
    server = StdioMCPServer(db_manager)
    await server.run()
