"""SSE/HTTP transport MCP server.

Provides MCP server functionality over HTTP Server-Sent Events (SSE) transport.
Future refactoring will move implementation from http_server.py here.
"""

import logging
import os
from typing import Optional, List
from mcp.server.sse import SseServerTransport
from database.manager import DatabaseManager
from protocol.base_server import BaseMCPServer
from core.config import get_http_config

logger = logging.getLogger(__name__)


class SseMCPServer(BaseMCPServer):
    """MCP server using HTTP/SSE transport."""

    def __init__(self, db_manager: DatabaseManager, messages_path: str = "/messages"):
        """Initialize SSE MCP server.

        Args:
            db_manager: DatabaseManager instance
            messages_path: Path for SSE messages endpoint (relative to mount point)
        """
        super().__init__(db_manager)
        self.sse_transport = SseServerTransport(messages_path)
        logger.info(f"SSE MCP server initialized with messages path: {messages_path}")

    async def handle_sse_connection(self, scope, receive, send):
        """Handle SSE connection.

        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        logger.info("Handling SSE connection")
        async with self.sse_transport.connect_sse(scope, receive, send) as streams:
            await self.server.run(
                streams[0],
                streams[1],
                self.server.create_initialization_options()
            )

    async def handle_messages(self, scope, receive, send):
        """Handle MCP messages endpoint.

        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        logger.info("Handling MCP messages")
        await self.sse_transport.handle_post_message(scope, receive, send)

    def create_asgi_app(self, allowed_origins: Optional[List[str]] = None):
        """Create ASGI application for SSE MCP with CORS support.

        Args:
            allowed_origins: List of allowed origins for CORS. If None, reads from env.

        Returns:
            ASGI callable that handles both SSE connection and messages with CORS
        """
        # Get CORS configuration with security awareness
        if allowed_origins is None:
            cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
            if cors_env:
                allowed_origins = [origin.strip() for origin in cors_env.split(",")]
            else:
                # Only provide defaults in development environment
                environment = os.getenv("ENVIRONMENT", "development")
                if environment == "development":
                    allowed_origins = ["http://localhost:3000", "http://localhost:8000"]
                    logger.info("SSE: 使用開發環境 CORS 預設值")
                else:
                    allowed_origins = []
                    logger.warning("SSE: ⚠️  生產環境未設定 CORS_ALLOWED_ORIGINS")

        async def app(scope, receive, send):
            path = scope.get("path", "/")
            method = scope.get("method", "GET")

            logger.debug(f"SSE MCP app: method={method}, path={path}")

            # Handle CORS preflight requests
            if method == "OPTIONS":
                await self._handle_cors_preflight(scope, receive, send, allowed_origins)
                return

            # Wrap send to add CORS headers
            original_send = send
            async def cors_send(message):
                if message['type'] == 'http.response.start':
                    headers = list(message.get('headers', []))
                    # Add CORS headers
                    origin = self._get_origin_from_scope(scope)
                    if origin and (origin in allowed_origins or "*" in allowed_origins):
                        headers.append((b'access-control-allow-origin', origin.encode()))
                        headers.append((b'access-control-allow-credentials', b'true'))
                    message['headers'] = headers
                await original_send(message)

            # SSE connection endpoint (typically mounted at /sse/)
            if method == "GET" and path.endswith("/"):
                await self.handle_sse_connection(scope, receive, cors_send)
            # Messages endpoint (typically /sse/messages)
            elif method == "POST" and "messages" in path:
                await self.handle_messages(scope, receive, cors_send)
            else:
                # 404 for unknown paths
                logger.warning(f"Unknown path in SSE MCP app: {method} {path}")
                await cors_send({
                    'type': 'http.response.start',
                    'status': 404,
                    'headers': [[b'content-type', b'text/plain']],
                })
                await cors_send({
                    'type': 'http.response.body',
                    'body': b'Not Found',
                })

        return app

    def _get_origin_from_scope(self, scope) -> Optional[str]:
        """Extract origin from ASGI scope headers."""
        headers = dict(scope.get('headers', []))
        origin = headers.get(b'origin')
        return origin.decode() if origin else None

    async def _handle_cors_preflight(self, scope, receive, send, allowed_origins: List[str]):
        """Handle CORS preflight (OPTIONS) requests."""
        origin = self._get_origin_from_scope(scope)
        http_config = get_http_config()

        headers = [
            (b'content-type', b'text/plain'),
            (b'content-length', b'0'),
        ]

        # Add CORS headers if origin is allowed
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            headers.extend([
                (b'access-control-allow-origin', origin.encode()),
                (b'access-control-allow-methods', b'GET, POST, OPTIONS'),
                (b'access-control-allow-headers', b'Content-Type, Authorization'),
                (b'access-control-allow-credentials', b'true'),
                (b'access-control-max-age', str(http_config.cors_preflight_max_age).encode()),
            ])

        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': headers,
        })
        await send({
            'type': 'http.response.body',
            'body': b'',
        })
