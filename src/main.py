"""Unified entry point for MCP Database Server.

This module provides a single entry point that can run in either:
- STDIO mode: For use with MCP clients via stdio transport
- HTTP mode: For use with REST API and SSE MCP transport

Usage:
    # STDIO mode (default)
    python main.py

    # HTTP mode
    python main.py --http

    # HTTP mode with custom host/port
    python main.py --http --host 0.0.0.0 --port 8000
"""

import asyncio
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_stdio_mode():
    """Run MCP server in STDIO mode.

    This mode is used for direct MCP client communication via stdio transport.
    Typically used when the server is spawned as a subprocess by an MCP client.
    """
    logger.info("Starting MCP Database Server in STDIO mode")

    from protocol.stdio_server import run_stdio_server
    try:
        await run_stdio_server()
    except Exception as e:
        logger.error(f"STDIO server error: {e}", exc_info=True)
        sys.exit(1)


async def run_http_mode(host: str = "0.0.0.0", port: int = 8000):
    """Run MCP server in HTTP mode with REST API and SSE support.

    Args:
        host: Host address to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 8000)

    This mode provides:
    - REST API endpoints for direct database operations
    - SSE (Server-Sent Events) MCP transport at /sse/
    - Full MCP protocol support via HTTP
    """
    logger.info(f"Starting MCP Database Server in HTTP mode on {host}:{port}")

    from fastapi import FastAPI
    import uvicorn

    from core.config import DatabaseConfig, AppConfig
    from database.manager import DatabaseManager
    from api.middleware import setup_middleware
    from api.routes import router as api_router
    from protocol.sse_server import SseMCPServer

    # Create configurations
    try:
        db_config = DatabaseConfig.from_env()
        app_config = AppConfig.from_env()
        logger.info(f"Configuration loaded: {db_config.db_type} @ {db_config.server}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Create database manager
    try:
        db_manager = DatabaseManager(db_config, app_config)
        # Initialize (including preload if configured)
        if app_config.schema_config.preload_on_startup:
            db_manager._try_schema_preload()
        logger.info("DatabaseManager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize DatabaseManager: {e}")
        sys.exit(1)

    # Test database connection
    test_result = db_manager.test_connection()
    if not test_result.get('success'):
        logger.warning("Database connection test failed")
        logger.warning(f"Error: {test_result.get('error')}")
    else:
        logger.info("Database connection test passed")

    # Create FastAPI application
    app = FastAPI(
        title="MCP Database API",
        version="2.0.0",
        description="Model Context Protocol (MCP) Database Server - Database Tools & REST API"
    )

    # Setup middleware (CORS, etc.)
    setup_middleware(app, app_config)

    # Include REST API routes
    app.include_router(api_router)
    logger.info("REST API routes registered")

    # Create and mount SSE MCP server
    mcp_sse_server = SseMCPServer(db_manager, messages_path="/messages")
    mcp_asgi_app = mcp_sse_server.create_asgi_app()
    app.mount("/sse", mcp_asgi_app)
    logger.info("MCP SSE server mounted at /sse/")

    # Add root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "MCP Database Server",
            "version": "2.0.0",
            "modes": ["REST API", "MCP SSE"],
            "endpoints": {
                "api": "/api/v1",
                "health": "/api/v1/health",
                "mcp_sse": "/sse/",
                "docs": "/docs"
            }
        }

    # Add graceful shutdown handler
    @app.on_event("shutdown")
    async def shutdown_event():
        """Gracefully shutdown the server and cleanup resources."""
        logger.info("Shutting down MCP Database Server...")

        # Clear schema cache if exists
        try:
            if hasattr(db_manager, 'schema_cache') and db_manager.schema_cache:
                db_manager.schema_cache.clear()
                logger.info("Schema cache cleared")
        except Exception as e:
            logger.warning(f"Error clearing schema cache: {e}")

        # Close database connections if needed
        try:
            if hasattr(db_manager, 'db_connector'):
                logger.info("Database connections cleanup completed")
        except Exception as e:
            logger.warning(f"Error closing database connections: {e}")

        logger.info("Graceful shutdown completed")

    # Run server
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except Exception as e:
        logger.error(f"HTTP server error: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point with argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP Database Server - Unified Entry Point"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run in HTTP mode (default: STDIO mode)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host address for HTTP mode (default: from HTTP_HOST env or 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for HTTP mode (default: from HTTP_PORT env or 8000)"
    )

    args = parser.parse_args()

    if args.http:
        # HTTP mode
        host = args.host or os.getenv("HTTP_HOST", "0.0.0.0")
        port = args.port or int(os.getenv("HTTP_PORT", "8000"))
        asyncio.run(run_http_mode(host, port))
    else:
        # STDIO mode (default)
        asyncio.run(run_stdio_mode())


if __name__ == "__main__":
    main()
