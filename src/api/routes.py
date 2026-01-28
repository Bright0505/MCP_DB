"""FastAPI routes for MCP Database REST API."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database.manager import DatabaseManager
from core.dependencies import get_db_manager_dependency

logger = logging.getLogger(__name__)


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


router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
async def health_check(db: DatabaseManager = Depends(get_db_manager_dependency)):
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
        version="2.0.0",
        database_connected=True
    )


@router.post("/query")
async def execute_query(
    request: QueryRequest,
    db: DatabaseManager = Depends(get_db_manager_dependency)
):
    """Execute a SQL query."""
    result = db.execute_query(request.query, request.params)
    return APIResponse(
        success=result.get("success", False),
        data=result if result.get("success") else None,
        error=result.get("error") if not result.get("success") else None,
        timestamp=datetime.now().isoformat()
    )


@router.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """List all available MCP tools."""
    from tools import get_all_tools
    tools = get_all_tools()
    return [
        ToolInfo(
            name=tool.name,
            description=tool.description,
            parameters=tool.inputSchema
        )
        for tool in tools
    ]


@router.get("/schema")
async def get_schema(
    table_name: Optional[str] = None,
    db: DatabaseManager = Depends(get_db_manager_dependency)
):
    """Get database schema information."""
    result = db.get_schema_info(table_name)
    return APIResponse(
        success=result.get("success", False),
        data=result if result.get("success") else None,
        error=result.get("error") if not result.get("success") else None,
        timestamp=datetime.now().isoformat()
    )


@router.post("/cache/invalidate")
async def invalidate_cache(
    request: CacheInvalidateRequest,
    db: DatabaseManager = Depends(get_db_manager_dependency)
):
    """Invalidate schema cache."""
    result = db.invalidate_schema_cache(request.table_name)
    return APIResponse(
        success=result.get("success", False),
        data=result if result.get("success") else None,
        error=result.get("error") if not result.get("success") else None,
        timestamp=datetime.now().isoformat()
    )


@router.get("/cache/stats")
async def get_cache_stats(db: DatabaseManager = Depends(get_db_manager_dependency)):
    """Get schema cache statistics."""
    result = db.get_schema_cache_stats()
    return APIResponse(
        success=result.get("success", False),
        data=result if result.get("success") else None,
        error=result.get("error") if not result.get("success") else None,
        timestamp=datetime.now().isoformat()
    )
