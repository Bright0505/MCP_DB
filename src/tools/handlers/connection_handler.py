"""Connection testing handler."""

import logging
from typing import Any, Dict, List
from mcp.types import CallToolRequest

from tools.base import ToolHandler
from tools.definitions import make_tool_name, TOOL_TEST_CONNECTION

logger = logging.getLogger(__name__)


class ConnectionHandler(ToolHandler):
    """Handler for database connection testing."""

    @property
    def tool_names(self) -> List[str]:
        return [make_tool_name(TOOL_TEST_CONNECTION)]

    async def handle(self, request: CallToolRequest, db_manager: Any) -> Dict[str, Any]:
        """
        Test database connection and return status asynchronously.

        Args:
            request: MCP tool call request
            db_manager: Database manager instance (HybridDatabaseManager)

        Returns:
            Connection test results with server information
        """
        # Test connection asynchronously (uses connection pool)
        result = await db_manager.test_connection_async()

        if result['success']:
            return self._format_success_response(result)
        else:
            return self._format_error_response(result)

    def _format_success_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format successful connection test result."""
        server_info = result.get('server_info', {})
        output = "✅ Connection test: Success\n\n"
        output += f"📡 Server: {server_info.get('server', 'N/A')}\n"
        output += f"💾 Database: {server_info.get('current_database', server_info.get('database', 'N/A'))}\n"
        output += f"🔌 Port: {server_info.get('port', 'N/A')}\n"
        output += f"🔒 Encryption: {'Enabled' if server_info.get('encrypt') else 'Disabled'}\n"
        output += f"🚗 Driver: {server_info.get('driver', 'N/A')}\n"
        
        if server_info.get('server_version'):
            version = server_info['server_version']
            output += f"📋 Server Version: {version[:100]}...\n" if len(version) > 100 else f"📋 Server Version: {version}\n"
        
        return self._success_response(output)

    def _format_error_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format failed connection test result."""
        error_msg = result.get('message') or result.get('error', 'Unknown error')
        output = "❌ Connection test: Failed\n\n"
        output += f"💬 Message: {error_msg}\n"
        
        if result.get('diagnostic'):
            output += f"🔍 Diagnostic: {result['diagnostic']}\n\n"
        
        if result.get('suggestions'):
            output += "💡 Suggestions:\n"
            for suggestion in result['suggestions']:
                output += f"   • {suggestion}\n"
            output += "\n"
        
        if result.get('connection_info'):
            conn_info = result['connection_info']
            output += "🔧 Connection Configuration:\n"
            output += f"   • Server: {conn_info.get('server', 'N/A')}\n"
            output += f"   • Database: {conn_info.get('database', 'N/A')}\n"
            output += f"   • Port: {conn_info.get('port', 'N/A')}\n"
            output += f"   • Driver: {conn_info.get('driver', 'N/A')}\n"
            output += f"   • Encryption: {'Enabled' if conn_info.get('encrypt') else 'Disabled'}\n"
        
        return {
            "content": [{
                "type": "text",
                "text": output
            }]
        }
