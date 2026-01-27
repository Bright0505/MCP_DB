"""HTTP server wrapper for MCP Multi-Database Connector.

Provides REST API access and MCP SSE (Server-Sent Events) support for external integrations.
"""

import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from starlette.routing import Mount, Route
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# MCP Imports
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, Prompt, Resource

# Internal Imports
from core.config import DatabaseConfig, HTTPConfig
from database.async_manager import HybridDatabaseManager
from database.schema.cache import CachedSchemaIntrospector
# Import tool definitions and handlers from tools layer
from mcp.types import CallToolRequest
from tools import POSDB_TOOLS, ToolRegistry, get_all_tools
from tools.validators import SQLValidator

# 設定日誌
logger = logging.getLogger(__name__)

# HTTP server constants
GZIP_MIN_SIZE = 1000  # Minimum response size for GZip compression (bytes)

# Pydantic 模型定義
class QueryRequest(BaseModel):
    query: str
    params: Optional[List[Any]] = None

class CacheInvalidateRequest(BaseModel):
    table_name: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    database_connected: bool
    
class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str


# ... (imports)
from starlette.applications import Starlette
from starlette.routing import Route

# ... (previous code)

class MCPHTTPServer:
    """HTTP server wrapper for MCP database tools with SSE support."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """初始化 HTTP 伺服器."""
        self.config = config or DatabaseConfig.from_env()
        self.http_config = HTTPConfig.from_env()
        self.db_manager = None

        # Initialize Tool Registry
        self.tool_registry = ToolRegistry()

        # Initialize MCP Server
        self.server_name = os.getenv("MCP_SERVER_NAME", "mcp-db")
        self.mcp_server = Server(self.server_name)
        # SSE transport path is relative to SSE mount point
        self.sse_transport = SseServerTransport("/messages")

        # Setup MCP handlers BEFORE creating SSE App
        self._setup_mcp_handlers()

        # 定義 lifespan 用於自動初始化
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup: 初始化資料庫和預載 schema
            await self.initialize()
            logger.info("🚀 服務啟動完成，Schema 已預載")
            yield
            # Shutdown: 清理資源
            logger.info("🛑 服務關閉")

        # Create Main FastAPI App with lifespan
        self.app = FastAPI(
            title="MCP Database API",
            description="REST API & SSE for Multi-Database Connector via MCP",
            version="1.2.0",
            docs_url="/docs",
            redoc_url="/redoc",
            lifespan=lifespan
        )

        # Create a combined ASGI app for MCP SSE that handles both /sse/ and /sse/messages
        async def mcp_sse_asgi_app(scope, receive, send):
            """Combined ASGI app for MCP SSE endpoints"""
            path = scope.get("path", "/")
            method = scope.get("method", "GET")

            logger.debug(f"MCP SSE app: method={method}, path={path}, type={scope.get('type')}")

            # SSE connection at /sse/
            if path == "/sse/" and method == "GET":
                logger.info("Handling SSE connection")
                async with self.sse_transport.connect_sse(scope, receive, send) as streams:
                    await self.mcp_server.run(
                        streams[0],
                        streams[1],
                        self.mcp_server.create_initialization_options()
                    )
            # MCP messages at /sse/messages
            elif path.startswith("/sse/messages") and method == "POST":
                logger.info("Handling MCP message")
                await self.sse_transport.handle_post_message(scope, receive, send)
            else:
                # 404 for unknown paths
                logger.warning(f"Unknown path in MCP SSE app: {method} {path}")
                await send({
                    'type': 'http.response.start',
                    'status': 404,
                    'headers': [[b'content-type', b'text/plain']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': b'Not Found',
                })

        # Mount the combined MCP SSE app at /sse
        self.app.mount("/sse", mcp_sse_asgi_app)

        # 添加 CORS 支援 (Main App Only)
        # 安全的 CORS 配置：生產環境必須明確設定
        cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
        if cors_env:
            allowed_origins = [origin.strip() for origin in cors_env.split(",")]
        else:
            # 只在開發環境提供預設值
            environment = os.getenv("ENVIRONMENT", "development")
            if environment == "development":
                allowed_origins = ["http://localhost:3000", "http://localhost:8000"]
                logger.info("使用開發環境 CORS 預設值: localhost:3000, localhost:8000")
            else:
                allowed_origins = []
                logger.warning("⚠️  生產環境未設定 CORS_ALLOWED_ORIGINS，CORS 已禁用")

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )

        # Setup rate limiting
        self.limiter = Limiter(key_func=get_remote_address)
        self.app.state.limiter = self.limiter
        self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("✅ Rate limiting enabled")

        # Add GZip compression for responses >1KB
        self.app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_SIZE)
        logger.info("✅ Response compression enabled (GZip)")

        # 註冊路由
        self._register_routes()

    # ... (rest of the class)

    def _setup_mcp_handlers(self):
        """設定 MCP 工具處理器."""
        # Register list_tools handler
        @self.mcp_server.list_tools()
        async def list_tools() -> List[Tool]:
            """返回可用工具列表."""
            return get_all_tools()

        # Register call_tool handler
        @self.mcp_server.call_tool()
        async def handle_tool_call(name: str, arguments: dict) -> list:
            """處理 MCP 工具調用."""
            if not self.db_manager:
                return [{"type": "text", "text": "Error: Database not initialized"}]

            try:
                # Create CallToolRequest-like object from parameters
                # Note: We use a simple object instead of mcp.types.CallToolRequest
                # because the MCP library provides name/arguments directly
                request = type('CallToolRequest', (), {
                    'name': name,
                    'arguments': arguments or {}
                })()
                # Route through tool registry
                result = await self.tool_registry.handle_tool(request, self.db_manager)
                # 確保返回格式符合 MCP 標準
                if isinstance(result, dict) and "content" in result:
                    return result["content"]  # Extract content list for MCP handler
                else:
                    # 包裝為正確格式 (fallback)
                    return result if isinstance(result, list) else [result]
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return [{"type": "text", "text": f"Error: {str(e)}"}]

        # Register list_prompts handler
        @self.mcp_server.list_prompts()
        async def list_prompts() -> List[Prompt]:
            """返回可用提示列表."""
            return []

        # Register list_resources handler
        @self.mcp_server.list_resources()
        async def list_resources() -> List[Resource]:
            """返回可用資源列表."""
            return []

    async def initialize(self):
        """初始化資料庫管理器（異步，支持連接池）."""
        # Initialize hybrid database manager (async + sync support with preload)
        self.db_manager = HybridDatabaseManager.create_with_preload()

        # 確保 schema 配置已載入（解決 MCPO SSE 連接問題）
        preload_result = self.db_manager.reload_schema_config()
        if preload_result.get("success"):
            logger.info("✅ Schema 配置預載成功")
        else:
            logger.warning(f"⚠️ Schema 配置預載失敗: {preload_result.get('message')}")

        # Test connection asynchronously
        result = await self.db_manager.test_connection_async()
        if result.get("success"):
            logger.info("✅ 資料庫連線測試成功（異步連接池）")
        else:
            logger.warning(f"⚠️ 資料庫連線測試失敗: {result.get('error')}")

    def _register_routes(self):
        """註冊所有 API 路由."""

        # Note: MCP Messages endpoint is now integrated within the SSE app at /sse/messages
        # (See SSE app initialization in __init__)

        # --- Existing REST API Routes ---
        # ... (keep all existing REST routes)
        
        # 健康檢查
        @self.app.get("/api/v1/health", response_model=HealthResponse)
        async def health_check():
            """健康檢查端點."""
            db_connected = False
            if self.db_manager:
                try:
                    result = self.db_manager.test_connection()
                    db_connected = result.get("success", False)
                except Exception:
                    pass
                    
            return HealthResponse(
                status="healthy" if db_connected else "degraded",
                timestamp=datetime.now().isoformat(),
                version="1.2.0",
                database_connected=db_connected
            )
        
        # 工具列表
        @self.app.get("/api/v1/tools")
        async def list_api_tools():
            """取得可用工具列表 (REST API 格式)."""
            # This is kept for backward compatibility with REST API users
            tools = [
                {
                    "name": "connection_test",
                    "endpoint": "/api/v1/connection/test",
                    "method": "GET",
                    "description": "測試資料庫連線狀態"
                },
                {
                    "name": "query",
                    "endpoint": "/api/v1/query",
                    "method": "POST",
                    "description": "執行 SELECT 查詢"
                },
                {
                    "name": "schema",
                    "endpoint": "/api/v1/schema",
                    "method": "GET",
                    "description": "取得完整資料庫 Schema"
                },
                {
                    "name": "table_schema",
                    "endpoint": "/api/v1/schema/{table_name}",
                    "method": "GET",
                    "description": "取得特定表格的 Schema"
                },
                {
                    "name": "dependencies",
                    "endpoint": "/api/v1/dependencies/{table_name}",
                    "method": "GET",
                    "description": "分析表格依賴關係"
                },
                {
                    "name": "summary",
                    "endpoint": "/api/v1/summary",
                    "method": "GET",
                    "description": "取得資料庫物件摘要統計"
                },
                {
                    "name": "database_info",
                    "endpoint": "/api/v1/database/info",
                    "method": "GET",
                    "description": "取得資料庫詳細資訊 (對應 MCP schema_summary 工具)"
                },
                {
                    "name": "cache_stats",
                    "endpoint": "/api/v1/cache/stats",
                    "method": "GET",
                    "description": "取得快取統計資訊"
                },
                {
                    "name": "cache_invalidate",
                    "endpoint": "/api/v1/cache/invalidate",
                    "method": "POST",
                    "description": "清除快取"
                },
                {
                    "name": "schema_reload",
                    "endpoint": "/api/v1/schema/reload",
                    "method": "POST",
                    "description": "重新載入 Schema 配置"
                },
                {
                    "name": "static_schema_info",
                    "endpoint": "/api/v1/schema/static/info",
                    "method": "GET",
                    "description": "取得靜態 Schema 檔案狀態"
                }
            ]
            return self._success_response(tools)
        
        # 連線測試
        @self.app.get("/api/v1/connection/test")
        async def test_connection():
            """測試資料庫連線（異步）."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")

            try:
                # Use async connection test (uses connection pool)
                result = await self.db_manager.test_connection_async()
                return self._success_response(result)
            except Exception as e:
                logger.error(f"連線測試失敗: {e}")
                return self._error_response(f"連線測試失敗: {str(e)}")
        
        # 查詢
        @self.app.post("/api/v1/query")
        @self.limiter.limit(self.http_config.rate_limit_query)
        async def execute_query(request: Request, query_request: QueryRequest):
            """執行 SELECT 查詢（異步，使用連接池）."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")

            # Security validation (Phase 4 - SQL injection prevention)
            is_valid, error_msg = SQLValidator.validate_query(query_request.query)
            if not is_valid:
                logger.warning(f"Query blocked by security validation: {error_msg}")
                return self._error_response(f"Security validation failed: {error_msg}")

            try:
                # Use async query execution (10-50x performance improvement with connection pool)
                result = await self.db_manager.execute_query_async(query_request.query, query_request.params or [])
                return self._success_response(result)
            except Exception as e:
                logger.error(f"查詢執行失敗: {e}")
                return self._error_response(f"查詢執行失敗: {str(e)}")
        
        # Schema - 全部表格
        @self.app.get("/api/v1/schema")
        async def get_schema():
            """取得完整資料庫 Schema."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")
                
            try:
                result = self.db_manager.get_schema_info()
                return self._success_response(result)
            except Exception as e:
                logger.error(f"Schema 查詢失敗: {e}")
                return self._error_response(f"Schema 查詢失敗: {str(e)}")
        
        # Schema - 特定表格
        @self.app.get("/api/v1/schema/{table_name}")
        async def get_table_schema(table_name: str):
            """取得特定表格的 Schema."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")
                
            try:
                result = self.db_manager.get_schema_info(table_name)
                return self._success_response(result)
            except Exception as e:
                logger.error(f"表格 Schema 查詢失敗: {e}")
                return self._error_response(f"表格 Schema 查詢失敗: {str(e)}")
        
        # 依賴關係分析
        @self.app.get("/api/v1/dependencies/{table_name}")
        async def get_table_dependencies(table_name: str):
            """分析表格依賴關係."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")
                
            try:
                result = self.db_manager.get_table_dependencies(table_name)
                return self._success_response(result)
            except Exception as e:
                logger.error(f"依賴關係分析失敗: {e}")
                return self._error_response(f"依賴關係分析失敗: {str(e)}")
        
        # 資料庫摘要
        @self.app.get("/api/v1/summary")
        async def get_database_summary():
            """取得資料庫物件摘要統計."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")

            try:
                result = self.db_manager.get_schema_summary()
                return self._success_response(result)
            except Exception as e:
                logger.error(f"資料庫摘要查詢失敗: {e}")
                return self._error_response(f"資料庫摘要查詢失敗: {str(e)}")

        # 資料庫詳細資訊 (對應 MCP schema_summary 工具)
        @self.app.get("/api/v1/database/info")
        async def get_database_info():
            """取得資料庫詳細資訊 (database_type, database_name, server_name, summary)."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")

            try:
                result = self.db_manager.get_database_info()
                return self._success_response(result)
            except Exception as e:
                logger.error(f"資料庫資訊查詢失敗: {e}")
                return self._error_response(f"資料庫資訊查詢失敗: {str(e)}")

        # 快取統計
        @self.app.get("/api/v1/cache/stats")
        async def get_cache_stats():
            """取得快取統計資訊."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")

            try:
                result = self.db_manager.get_cache_stats()
                return self._success_response(result)
            except Exception as e:
                logger.error(f"快取統計查詢失敗: {e}")
                return self._error_response(f"快取統計查詢失敗: {str(e)}")

        # 快取調試資訊
        @self.app.get(
            "/api/v1/admin/cache-debug",
            summary="Get Cache Debug Info",
            description="取得詳細的快取調試資訊，包含快取實例 ID、快取鍵列表、快取詳情等.",
            operation_id="get_cache_debug_info_api_v1_admin_cache_debug_get",
            tags=["Cache Management"]
        )
        async def get_cache_debug():
            """取得詳細的快取調試資訊，用於診斷快取共享問題."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")

            try:
                result = self.db_manager.get_cache_debug_info()
                return self._success_response(result)
            except Exception as e:
                logger.error(f"快取調試查詢失敗: {e}")
                return self._error_response(f"快取調試查詢失敗: {str(e)}")

        # 快取失效
        @self.app.post("/api/v1/cache/invalidate")
        async def invalidate_cache(request: CacheInvalidateRequest):
            """清除快取."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")
                
            try:
                result = self.db_manager.invalidate_schema_cache(request.table_name)
                return self._success_response(result)
            except Exception as e:
                logger.error(f"快取清除失敗: {e}")
                return self._error_response(f"快取清除失敗: {str(e)}")
        
        # Schema 重載
        @self.app.post("/api/v1/schema/reload")
        async def reload_schema_config():
            """重新載入 Schema 配置."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")
                
            try:
                result = self.db_manager.reload_schema_config()
                return self._success_response(result)
            except Exception as e:
                logger.error(f"Schema 重載失敗: {e}")
                return self._error_response(f"Schema 重載失敗: {str(e)}")
        
        # 靜態 Schema 資訊
        @self.app.get("/api/v1/schema/static/info")
        async def get_static_schema_info():
            """取得靜態 Schema 檔案狀態."""
            if not self.db_manager:
                raise HTTPException(status_code=503, detail="Database manager not initialized")
                
            try:
                result = self.db_manager.get_static_schema_info()
                return self._success_response(result)
            except Exception as e:
                logger.error(f"靜態 Schema 資訊查詢失敗: {e}")
                return self._error_response(f"靜態 Schema 資訊查詢失敗: {str(e)}")

    def _success_response(self, data: Any) -> Dict[str, Any]:
        """建立成功回應."""
        return {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """建立錯誤回應."""
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat()
        }


async def create_server(config: Optional[DatabaseConfig] = None) -> MCPHTTPServer:
    """建立並初始化 HTTP 伺服器.

    注意：此函數會手動調用 initialize()，適用於不使用 uvicorn 的情況。
    如果使用 uvicorn 啟動，lifespan 會自動處理初始化。
    """
    server = MCPHTTPServer(config)
    await server.initialize()
    return server


def run_http_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    config: Optional[DatabaseConfig] = None
):
    """執行 HTTP 伺服器."""
    async def start_server():
        # 只創建 server，不手動調用 initialize()
        # lifespan 會在 uvicorn 啟動時自動處理初始化
        server = MCPHTTPServer(config)

        # 設定日誌
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        logger.info(f"🌐 啟動 MCP Database HTTP API + SSE 伺服器...")
        logger.info(f"📍 伺服器地址: http://{host}:{port}")
        logger.info(f"📚 API 文檔: http://{host}:{port}/docs")
        logger.info(f"🔌 MCP SSE 端點: http://{host}:{port}/sse")

        # 執行伺服器 (lifespan 會自動調用 initialize)
        config_uvicorn = uvicorn.Config(
            server.app,
            host=host,
            port=port,
            log_level="info"
        )
        server_uvicorn = uvicorn.Server(config_uvicorn)
        await server_uvicorn.serve()

    # 執行非同步伺服器
    asyncio.run(start_server())


if __name__ == "__main__":
    # 從環境變數讀取設定
    host = os.getenv("HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("HTTP_PORT", "8000"))
    
    # 執行伺服器
    run_http_server(host, port)