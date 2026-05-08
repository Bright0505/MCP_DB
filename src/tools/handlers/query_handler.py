"""Query execution handler with security validation."""

import logging
from typing import Any, Dict, List
from mcp.types import CallToolRequest

from tools.base import ToolHandler
from tools.definitions import make_tool_name, TOOL_QUERY
from tools.validators import SQLValidator

logger = logging.getLogger(__name__)


class QueryHandler(ToolHandler):
    """Handler for database query execution."""

    @property
    def tool_names(self) -> List[str]:
        return [make_tool_name(TOOL_QUERY)]

    async def handle(self, request: CallToolRequest, db_manager: Any) -> Dict[str, Any]:
        """
        Execute SQL SELECT query with security validation.

        Args:
            request: MCP tool call request
            db_manager: Database manager instance

        Returns:
            Formatted query results or error message
        """
        query = request.arguments.get("query")
        params = request.arguments.get("params")

        # Validate query parameter
        if not query:
            return self._error_response("Query parameter is required")

        # Security validation (NEW - prevents SQL injection and dangerous operations)
        is_valid, error_msg = SQLValidator.validate_query(query)
        if not is_valid:
            logger.warning(f"Query blocked by security validation: {error_msg}")
            return self._error_response(f"Security validation failed: {error_msg}")

        # Execute query asynchronously (uses connection pool for performance)
        result = await db_manager.execute_query_async(query, params)

        # Format response
        return self._format_query_result(result, query)

    def _format_query_result(self, result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Format query execution result for MCP response."""
        if result["success"]:
            output = "✅ Query executed successfully\n"
            output += f"📊 Rows returned: {result['row_count']}\n"
            output += f"📋 Columns: {', '.join(result['columns'])}\n\n"

            if result["results"]:
                output += "📋 Results:\n"
                # Display up to 200 rows for LLM consumption
                display_limit = 200
                for i, row in enumerate(result["results"][:display_limit]):
                    output += f"Row {i+1}: {row}\n"

                if len(result["results"]) > display_limit:
                    output += f"... and {len(result['results']) - display_limit} more rows\n"
            else:
                output += "📋 No results returned\n"

            return self._success_response(output)
        else:
            # Error case
            error_msg = (result.get('message') or '').strip()
            # 防禦：若 message 為空、或為「Query execution failed:」尾端冒號（代表 str(e) 為空）
            if not error_msg or error_msg.rstrip(':').strip() in ('', 'Query execution failed'):
                error_msg = result.get('error') or 'Unknown error (empty exception, possible timeout or connection drop)'
            output = f"❌ Query failed: {error_msg}\n\n"

            # Include query for debugging
            output += "📝 Query:\n"
            output += f"```sql\n{query}\n```\n"

            return {
                "content": [{
                    "type": "text",
                    "text": output
                }]
            }
