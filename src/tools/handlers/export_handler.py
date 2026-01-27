"""Schema export handlers."""

import logging
from typing import Any, Dict, List
from mcp.types import CallToolRequest

from tools.base import ToolHandler
from tools.definitions import make_tool_name, TOOL_EXPORT_SCHEMA, TOOL_STATIC_SCHEMA_INFO
from tools.validators import InputValidator

logger = logging.getLogger(__name__)


class ExportHandler(ToolHandler):
    """Handler for schema export and static schema info."""

    @property
    def tool_names(self) -> List[str]:
        return [
            make_tool_name(TOOL_EXPORT_SCHEMA),
            make_tool_name(TOOL_STATIC_SCHEMA_INFO)
        ]

    async def handle(self, request: CallToolRequest, db_manager: Any) -> Dict[str, Any]:
        """
        Handle schema export operations.

        Args:
            request: MCP tool call request
            db_manager: Database manager instance

        Returns:
            Export operation results
        """
        if request.name == make_tool_name(TOOL_EXPORT_SCHEMA):
            return self._handle_export_schema(request, db_manager)
        elif request.name == make_tool_name(TOOL_STATIC_SCHEMA_INFO):
            return self._handle_static_schema_info(db_manager)
        else:
            return self._error_response(f"Unknown export operation: {request.name}")

    def _handle_export_schema(self, request: CallToolRequest, db_manager: Any) -> Dict[str, Any]:
        """Export table schema to file."""
        table_name = request.arguments.get("table_name")
        output_dir = request.arguments.get("output_dir", "schema_export")
        include_business_logic = request.arguments.get("include_business_logic", True)
        
        if not table_name:
            return self._error_response("Table name parameter is required")
        
        # Validate table name
        is_valid, error_msg = InputValidator.validate_table_name(table_name)
        if not is_valid:
            return self._error_response(error_msg)
        
        result = db_manager.export_table_schema(
            table_name=table_name,
            output_dir=output_dir,
            include_business_logic=include_business_logic
        )
        
        if result.get("success"):
            output = f"✅ Schema exported successfully\n\n"
            output += f"📁 File: {result.get('file_path', 'N/A')}\n"
            output += f"📋 Table: {table_name}\n"
            output += f"📊 Columns: {result.get('column_count', 0)}\n"
            return self._success_response(output)
        else:
            error_msg = result.get("message", "Unknown error")
            return self._error_response(f"Export failed: {error_msg}")

    def _handle_static_schema_info(self, db_manager: Any) -> Dict[str, Any]:
        """Get static schema file information."""
        result = db_manager.get_static_schema_info()
        
        if not result.get("success"):
            error_msg = result.get("message", "Unknown error")
            return self._error_response(f"Failed to get static schema info: {error_msg}")
        
        output = "📁 Static Schema Configuration\n\n"
        output += f"📂 Directory: {result.get('schema_directory', 'N/A')}\n"
        output += f"📊 Total Tables: {result.get('total_tables', 0)}\n"
        output += f"📋 Total Columns: {result.get('total_columns', 0)}\n\n"
        
        if result.get('sample_tables'):
            output += "📋 Sample Tables:\n"
            for table in result['sample_tables'][:10]:
                output += f"   • {table}\n"
        
        return self._success_response(output)
