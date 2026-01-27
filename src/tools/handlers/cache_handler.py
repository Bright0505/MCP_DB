"""Cache management handlers."""

import logging
from typing import Any, Dict, List
from mcp.types import CallToolRequest

from tools.base import ToolHandler
from tools.definitions import make_tool_name, TOOL_CACHE_STATS, TOOL_CACHE_INVALIDATE, TOOL_SCHEMA_RELOAD

logger = logging.getLogger(__name__)


class CacheHandler(ToolHandler):
    """Handler for schema cache operations."""

    @property
    def tool_names(self) -> List[str]:
        return [
            make_tool_name(TOOL_CACHE_STATS),
            make_tool_name(TOOL_CACHE_INVALIDATE),
            make_tool_name(TOOL_SCHEMA_RELOAD)
        ]

    async def handle(self, request: CallToolRequest, db_manager: Any) -> Dict[str, Any]:
        """
        Handle cache-related operations.

        Args:
            request: MCP tool call request
            db_manager: Database manager instance

        Returns:
            Cache operation results
        """
        if request.name == make_tool_name(TOOL_CACHE_STATS):
            return self._handle_cache_stats(db_manager)
        elif request.name == make_tool_name(TOOL_CACHE_INVALIDATE):
            table_name = request.arguments.get("table_name")
            return self._handle_cache_invalidate(db_manager, table_name)
        elif request.name == make_tool_name(TOOL_SCHEMA_RELOAD):
            return self._handle_schema_reload(db_manager)
        else:
            return self._error_response(f"Unknown cache operation: {request.name}")

    def _handle_cache_stats(self, db_manager: Any) -> Dict[str, Any]:
        """Get cache statistics."""
        result = db_manager.get_cache_debug_info()
        
        if not result.get("success"):
            return self._error_response("Failed to get cache stats")
        
        output = "📊 Schema Cache Statistics\n\n"
        output += f"🔧 Configuration:\n"
        output += f"   • Cache Enabled: {result.get('cache_enabled', False)}\n"
        output += f"   • TTL: {result.get('cache_ttl_minutes', 0)} minutes\n"
        output += f"   • Max Size: {result.get('max_cache_size', 0)}\n"
        output += f"   • Preload Enabled: {result.get('preload_enabled', False)}\n\n"
        
        output += f"📈 Statistics:\n"
        output += f"   • Total Entries: {result.get('total_entries', 0)}\n"
        output += f"   • Static Preloaded: {result.get('static_preloaded_count', 0)}\n"
        output += f"   • Dynamic Preloaded: {result.get('dynamic_preloaded_count', 0)}\n"
        
        if result.get('preload_status'):
            status = result['preload_status']
            output += f"\n🔄 Preload Status:\n"
            output += f"   • Static Complete: {status.get('static_preload_completed', False)}\n"
            output += f"   • Dynamic Complete: {status.get('dynamic_preload_completed', False)}\n"
        
        return self._success_response(output)

    def _handle_cache_invalidate(self, db_manager: Any, table_name: str = None) -> Dict[str, Any]:
        """Invalidate cache entries."""
        if table_name:
            result = db_manager.invalidate_schema_cache(table_name)
            if result.get("success"):
                return self._success_response(f"✅ Cache invalidated for table: {table_name}")
            else:
                return self._error_response(f"Failed to invalidate cache for {table_name}")
        else:
            # Clear all cache
            result = db_manager.clear_all_cache()
            if result.get("success"):
                cleared = result.get("cleared_count", 0)
                return self._success_response(f"✅ All cache cleared ({cleared} entries removed)")
            else:
                return self._error_response("Failed to clear cache")

    def _handle_schema_reload(self, db_manager: Any) -> Dict[str, Any]:
        """Reload schema configuration."""
        result = db_manager.reload_schema_config()
        
        if result.get("success"):
            output = "✅ Schema configuration reloaded\n\n"
            if result.get("preloaded_tables"):
                count = len(result["preloaded_tables"])
                output += f"📋 Preloaded {count} table schemas\n"
            return self._success_response(output)
        else:
            error_msg = result.get("message", "Unknown error")
            return self._error_response(f"Schema reload failed: {error_msg}")
