"""Table dependency analysis handler."""

import logging
from typing import Any, Dict, List
from mcp.types import CallToolRequest

from tools.base import ToolHandler
from tools.definitions import make_tool_name, TOOL_DEPENDENCIES
from tools.validators import InputValidator

logger = logging.getLogger(__name__)


class DependencyHandler(ToolHandler):
    """Handler for analyzing table dependencies."""

    @property
    def tool_names(self) -> List[str]:
        return [make_tool_name(TOOL_DEPENDENCIES)]

    async def handle(self, request: CallToolRequest, db_manager: Any) -> Dict[str, Any]:
        """
        Analyze table dependencies (foreign keys and references).

        Args:
            request: MCP tool call request
            db_manager: Database manager instance

        Returns:
            Dependency analysis results
        """
        table_name = request.arguments.get("table_name")
        
        if not table_name:
            return self._error_response("Table name parameter is required")
        
        # Validate table name
        is_valid, error_msg = InputValidator.validate_table_name(table_name)
        if not is_valid:
            return self._error_response(error_msg)
        
        result = db_manager.get_table_dependencies(table_name)
        return self._format_dependencies(result, table_name)

    def _format_dependencies(self, result: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Format dependency analysis result."""
        if not result["success"]:
            error_msg = result.get('message') or result.get('error', 'Unknown error')
            return self._error_response(f"Dependency query failed: {error_msg}")
        
        output = f"✅ Dependencies for table '{table_name}':\n\n"
        
        # Tables this table depends on
        depends_on = result.get("depends_on", [])
        if depends_on:
            output += "📤 This table depends on:\n"
            for dep in depends_on:
                output += f"   • {dep['REFERENCED_TABLE_NAME']}.{dep['REFERENCED_COLUMN_NAME']} ← {dep['COLUMN_NAME']} ({dep['CONSTRAINT_NAME']})\n"
        else:
            output += "📤 This table has no dependencies (no foreign keys)\n"
        
        output += "\n"
        
        # Tables that depend on this table
        referenced_by = result.get("referenced_by", [])
        if referenced_by:
            output += "📥 This table is referenced by:\n"
            for ref in referenced_by:
                output += f"   • {ref['TABLE_NAME']}.{ref['COLUMN_NAME']} → {ref['REFERENCED_COLUMN_NAME']} ({ref['CONSTRAINT_NAME']})\n"
        else:
            output += "📥 No other tables reference this table\n"
        
        return self._success_response(output)
