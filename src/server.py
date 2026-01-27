"""MCP server implementation for Multi-Database Connector."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    Tool,
    Prompt,
    Resource
)

from core.config import DatabaseConfig, AppConfig
from database.async_manager import HybridDatabaseManager
from tools.registry import ToolRegistry
from tools.definitions import POSDB_TOOLS as TOOLS_DEFINITIONS, get_key_tables_description, make_tool_name, get_tool_prefix
from tools.definitions import (
    TOOL_QUERY, TOOL_SCHEMA, TOOL_TEST_CONNECTION, TOOL_DEPENDENCIES,
    TOOL_SCHEMA_SUMMARY, TOOL_CACHE_STATS, TOOL_CACHE_INVALIDATE,
    TOOL_SCHEMA_RELOAD, TOOL_STATIC_SCHEMA_INFO, TOOL_EXPORT_SCHEMA,
    TOOL_SYNTAX_GUIDE
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Display limits for LLM context optimization
MAX_ROWS_FOR_LLM = 200  # Maximum rows to display in LLM context
MAX_TABLES_PREVIEW = 10  # Number of tables to show in preview

# Global database manager (Hybrid: supports both sync and async)
db_manager: Optional[HybridDatabaseManager] = None

# Global tool registry for modular tool handlers
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        logger.info("✅ Tool registry initialized")
    return _tool_registry


def get_db_manager() -> HybridDatabaseManager:
    """Get or create hybrid database manager instance with preload support and error handling."""
    global db_manager
    if db_manager is None:
        # Use the hybrid manager factory method (includes preload)
        db_manager = HybridDatabaseManager.create_with_preload()
        logger.info("✅ Hybrid database manager initialized successfully (sync + async support)")
    return db_manager


def load_sql_patterns() -> Dict[str, Any]:
    """Load SQL Server patterns from schemas_config."""
    import json
    from pathlib import Path
    import os

    try:
        # Use SCHEMA_CONFIG_PATH environment variable or default path
        schema_config_path = os.getenv('SCHEMA_CONFIG_PATH', 'schemas_config')
        patterns_path = Path(schema_config_path) / "global_patterns.json"
        if patterns_path.exists():
            with open(patterns_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('time_patterns', {})
    except Exception as e:
        logger.warning(f"Could not load SQL patterns: {e}")
    return {}


# Import MCP tools from definitions module
POSDB_TOOLS = TOOLS_DEFINITIONS

# Original tool definitions moved to tools/definitions.py
"""
Legacy tool definitions (now in tools/definitions.py):
[
    Tool(
        name="posdb_query",
        description=(
            "Execute a SELECT query on SQL Server (MSSQL) database and return results. "
            "READ-ONLY: Only SELECT queries are supported. "
            "\n\n"
            "DATABASE TYPE: Microsoft SQL Server (T-SQL syntax)\n"
            "- Use GETDATE() for current date (NOT CURDATE() or NOW())\n"
            "- Use DATEADD(), DATEDIFF(), YEAR(), MONTH(), DAY() for date operations\n"
            "- Use TOP N instead of LIMIT\n"
            "\n"
            "IMPORTANT: Before querying, use 'posdb_schema' or 'posdb_schema_summary' "
            "to discover available tables and columns. Do NOT guess table names. "
            "Common tables: SALE00 (sales master), SALE01 (sales detail), PRODUCT00, etc."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The SELECT SQL query to execute (read-only)"
                },
                "params": {
                    "type": "array",
                    "description": "Optional parameters for parameterized queries",
                    "items": {"type": "string"}
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="posdb_schema",
        description=(
            "Get detailed SQL Server database schema information. "
            "USE THIS FIRST before writing queries to discover available tables and their structure. "
            "\n"
            "DATABASE: SQL Server (use T-SQL syntax with GETDATE(), TOP N, etc.)\n"
            "\n"
            "Provide 'table_name' for specific table details, or omit it to list all available tables."
            "Key tables: SALE00 (销售主档), SALE01 (销售明细), PRODUCT00 (商品主档), SHOP00 (店铺), etc."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Optional table name to get specific table schema. Omit to list all available tables."
                }
            },
            "required": []
        }
    ),
    Tool(
        name="posdb_test_connection",
        description="Test the connection to database",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="posdb_dependencies",
        description="Get table dependencies (foreign keys and tables that reference this table)",
        inputSchema={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The name of the table to analyze dependencies for"
                }
            },
            "required": ["table_name"]
        }
    ),
    Tool(
        name="posdb_schema_summary",
        description=(
            "Get a high-level overview of all database objects (tables, views, procedures, functions). "
            "RECOMMENDED FIRST STEP: Use this to understand the database structure before querying. "
            "Returns counts and types of objects available in the database."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="posdb_cache_stats",
        description="Get schema cache statistics and configuration",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="posdb_cache_invalidate",
        description="Invalidate schema cache entries",
        inputSchema={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Optional table name to invalidate specific cache, or omit to clear all cache"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="posdb_schema_reload",
        description="Reload schema configuration and re-preload schemas",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="posdb_static_schema_info",
        description="Get information about static schema files",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="posdb_export_schema",
        description="Export table schema to standard documentation file",
        inputSchema={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table to export (required)"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Output directory for the schema file (optional, defaults to 'schema_export')"
                },
                "include_business_logic": {
                    "type": "boolean",
                    "description": "Include business logic descriptions (optional, defaults to true)"
                }
            },
            "required": ["table_name"]
        }
    ),
    Tool(
        name="posdb_syntax_guide",
        description=(
            "Get SQL Server (T-SQL) syntax reference and common query patterns for this database. "
            "Use this to learn the correct syntax before writing queries."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
]
"""


async def handle_call_tool(
    request: CallToolRequest,
    db_manager: Optional[HybridDatabaseManager] = None
) -> dict:
    """Handle MCP tool calls (supports optional db_manager with async capabilities)."""
    try:
        db = db_manager if db_manager is not None else get_db_manager()

        # Try modular tool registry first (NEW - Progressive Migration)
        registry = get_tool_registry()
        if registry.is_tool_registered(request.name):
            result = await registry.handle_tool(request, db)
            if result is not None:
                return result

        # Fallback to legacy handling for tools not yet migrated
        if request.name == make_tool_name(TOOL_TEST_CONNECTION):
            result = db.test_connection()
            
            if result['success']:
                server_info = result.get('server_info', {})
                output = "✅ Connection test: Success\n\n"
                output += f"📡 Server: {server_info.get('server', 'N/A')}\n"
                output += f"💾 Database: {server_info.get('current_database', server_info.get('database', 'N/A'))}\n"
                output += f"🔌 Port: {server_info.get('port', 'N/A')}\n"
                output += f"🔒 Encryption: {'Enabled' if server_info.get('encrypt') else 'Disabled'}\n"
                output += f"🚗 Driver: {server_info.get('driver', 'N/A')}\n"
                if server_info.get('server_version'):
                    output += f"📋 Server Version: {server_info['server_version'][:100]}...\n"
            else:
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
                    
                    if conn_info.get('connection_string'):
                        output += f"   • Connection String: {conn_info['connection_string']}\n"
                
                if result.get('error_code'):
                    output += f"\n🚨 Error Code: {result['error_code']}\n"
                
                output += f"\n❗ Error Details: {result.get('error', 'Unknown error')}"
            
            return {
                "content": [{"type": "text", "text": output}]
            }
        
        elif request.name == make_tool_name(TOOL_QUERY):
            query = request.arguments.get("query")
            params = request.arguments.get("params")
            
            if not query:
                return {
                    "content": [{"type": "text", "text": "❌ Error: Query parameter is required"}]
                }
            
            result = db.execute_query(query, params)
            
            if result["success"]:
                output = f"✅ Query executed successfully\n"
                output += f"📊 Rows returned: {result['row_count']}\n"
                output += f"📋 Columns: {', '.join(result['columns'])}\n\n"
                
                if result["results"]:
                    output += "📋 Results:\n"
                    # Display up to MAX_ROWS_FOR_LLM rows for LLM consumption
                    for i, row in enumerate(result["results"][:MAX_ROWS_FOR_LLM]):
                        output += f"Row {i+1}: {row}\n"

                    if len(result["results"]) > MAX_ROWS_FOR_LLM:
                        output += f"... and {len(result['results']) - MAX_ROWS_FOR_LLM} more rows\n"
                else:
                    output += "📋 No results returned\n"
            else:
                error_msg = result.get('message') or result.get('error', 'Unknown error')
                output = f"❌ Query failed: {error_msg}\n\n"

                if result.get('error_type'):
                    output += f"🔍 Error Type: {result['error_type']}\n"

                if result.get('suggestions'):
                    output += "\n💡 Suggestions:\n"
                    for suggestion in result['suggestions']:
                        output += f"   • {suggestion}\n"

                if result.get('query'):
                    output += f"\n📝 Query: {result['query'][:200]}..."
            
            return {"content": [{"type": "text", "text": output}]}

        elif request.name == make_tool_name(TOOL_SCHEMA):
            table_name = request.arguments.get("table_name")
            result = db.get_schema_info(table_name)
            
            if result["success"]:
                if table_name:
                    db_type = result.get('database_type', 'mssql')
                    db_type_display = 'SQL Server (T-SQL)' if db_type == 'mssql' else 'PostgreSQL'

                    output = f"✅ Schema for table '{table_name}':\n"
                    output += f"🗄️  Database: {db_type_display}\n\n"

                    # Show table statistics if available
                    if result.get("table_stats"):
                        stats = result["table_stats"]
                        output += f"📊 Table Statistics:\n"
                        output += f"   • Rows: {stats['row_count']:,}\n"
                        output += f"   • Size: {stats['size_mb']:.2f} MB\n\n"
                    
                    # Show Business Logic & AI Context (Enhanced from schemas_config)
                    if result.get("business_logic"):
                        logic = result["business_logic"]
                        output += "💼 Business Logic:\n"
                        if logic.get("primary_date_field"):
                            output += f"   • Primary Date: {logic['primary_date_field']}\n"
                        if logic.get("active_records_filter"):
                            output += f"   • Active Filter: {logic['active_records_filter']}\n"
                        if logic.get("status_values"):
                            status_str = ", ".join([f"{k}={v}" for k, v in logic["status_values"].items()])
                            output += f"   • Status Values: {status_str}\n"
                        if logic.get("main_business_rules"):
                            output += "   • Rules:\n"
                            for rule in logic["main_business_rules"]:
                                output += f"     - {rule}\n"
                        output += "\n"

                    if result.get("ai_context"):
                        ctx = result["ai_context"]
                        output += "🤖 AI Context (Prompt Injection):\n"
                        if ctx.get("query_keywords"):
                            output += f"   • Keywords: {', '.join(ctx['query_keywords'])}\n"
                        if ctx.get("common_filters"):
                            output += "   • Common Filters:\n"
                            for filter_txt in ctx["common_filters"]:
                                output += f"     - {filter_txt}\n"
                        if ctx.get("suggested_joins"):
                            output += "   • Suggested Joins:\n"
                            for join in ctx["suggested_joins"]:
                                output += f"     - {join}\n"
                        output += "\n"
                    
                    output += f"📋 Columns ({result['total_count']}):\n"
                    for column in result["results"]:
                        # Column name and type
                        col_name = column.get('COLUMN_NAME', 'unknown')
                        col_type = column.get('DATA_TYPE') or column.get('data_type', 'unknown')
                        col_info = f"   • {col_name}: {col_type}"
                        
                        # Add length/precision info
                        if column.get('CHARACTER_MAXIMUM_LENGTH'):
                            col_info += f"({column['CHARACTER_MAXIMUM_LENGTH']})"
                        elif column.get('NUMERIC_PRECISION'):
                            precision = column['NUMERIC_PRECISION']
                            scale = column.get('NUMERIC_SCALE', 0)
                            col_info += f"({precision},{scale})"
                        
                        # Nullable info
                        is_nullable = column.get('IS_NULLABLE', column.get('is_nullable', 'YES'))
                        col_info += f" {'NULL' if is_nullable == 'YES' else 'NOT NULL'}"
                        
                        # Key constraints
                        if column.get('IS_PRIMARY_KEY') == 'YES':
                            col_info += " 🔑 PK"
                        if column.get('IS_FOREIGN_KEY') == 'YES':
                            ref_table = column.get('REFERENCED_TABLE_NAME')
                            ref_column = column.get('REFERENCED_COLUMN_NAME')
                            col_info += f" 🔗 FK → {ref_table}.{ref_column}"
                        
                        # Default value
                        if column.get('COLUMN_DEFAULT'):
                            col_info += f" DEFAULT {column['COLUMN_DEFAULT']}"
                        
                        output += col_info
                        
                        # Add description and remarks
                        description_parts = []
                        if column.get('DESCRIPTION') and column['DESCRIPTION'].strip():
                            description_parts.append(f"📝 {column['DESCRIPTION'].strip()}")
                        if column.get('REMARKS') and column['REMARKS'].strip():
                            description_parts.append(f"💬 {column['REMARKS'].strip()}")
                        if column.get('REMARKS2') and column['REMARKS2'].strip():
                            description_parts.append(f"📋 {column['REMARKS2'].strip()}")
                        
                        if description_parts:
                            output += f" - {' | '.join(description_parts)}"
                        
                        output += "\n"
                else:
                    # Show all tables
                    db_type = result.get('database_type', 'unknown')
                    db_type_display = {
                        'mssql': 'SQL Server (T-SQL)',
                        'postgresql': 'PostgreSQL'
                    }.get(db_type, db_type)

                    output = f"✅ Database schema (showing {result['total_count']} objects):\n\n"
                    output += f"🗄️  Database Type: {db_type_display}\n"
                    output += f"📝 Syntax Guide: Use GETDATE() for current date, TOP N for limits, T-SQL functions\n"

                    # Load and show SQL patterns from config
                    try:
                        sql_patterns = load_sql_patterns()
                        if sql_patterns and db_type == 'mssql':
                            current_month_pattern = sql_patterns.get('current_month', {}).get('sql_server', '')
                            if current_month_pattern:
                                output += f"💡 Current month query example: {current_month_pattern}\n"
                    except Exception:
                        pass  # Silently ignore pattern loading errors

                    output += "\n"

                    # Group by schema and type
                    tables = {}
                    total_rows = 0
                    total_size = 0.0
                    
                    for obj in result["results"]:
                        schema = obj['TABLE_SCHEMA']
                        obj_type = obj['TABLE_TYPE']

                        # Normalize table type: 'TABLE' -> 'BASE TABLE'
                        if obj_type == 'TABLE':
                            obj_type = 'BASE TABLE'

                        if schema not in tables:
                            tables[schema] = {'BASE TABLE': [], 'VIEW': []}
                        
                        size_mb_raw = obj.get('SIZE_MB', 0.0)
                        rows_raw = obj.get('ROW_COUNT', 0)
                        obj_info = {
                            'name': obj['TABLE_NAME'],
                            'rows': int(rows_raw) if rows_raw is not None else 0,
                            'size_mb': float(size_mb_raw) if size_mb_raw is not None else 0.0
                        }
                        
                        if obj_type in tables[schema]:
                            tables[schema][obj_type].append(obj_info)
                        
                        if obj_type == 'BASE TABLE':
                            total_rows += obj_info['rows'] or 0
                            size_mb = obj_info['size_mb'] or 0.0
                            total_size += float(size_mb) if size_mb is not None else 0.0
                    
                    # Show summary
                    if total_rows > 0 or total_size > 0:
                        output += f"📊 Summary: {total_rows:,} total rows, {total_size:.2f} MB total size\n\n"
                    
                    # Show objects by schema
                    for schema, types in tables.items():
                        output += f"📂 Schema: {schema}\n"
                        
                        if types['BASE TABLE']:
                            output += f"   📋 Tables ({len(types['BASE TABLE'])}):\n"
                            for table in types['BASE TABLE']:
                                size_info = f" ({table['rows']:,} rows, {table['size_mb']:.1f} MB)" if table['rows'] or table['size_mb'] else ""
                                output += f"      • {table['name']}{size_info}\n"
                        
                        if types['VIEW']:
                            output += f"   👁️ Views ({len(types['VIEW'])}):\n"
                            for view in types['VIEW']:
                                output += f"      • {view['name']}\n"
                        
                        output += "\n"
            else:
                error_msg = result.get('message') or result.get('error', 'Unknown error')
                output = f"❌ Schema query failed: {error_msg}"

            return {"content": [{"type": "text", "text": output}]}
        
        elif request.name == make_tool_name(TOOL_DEPENDENCIES):
            table_name = request.arguments.get("table_name")
            
            if not table_name:
                return {
                    "content": [{"type": "text", "text": "❌ Error: Table name parameter is required"}]
                }
            
            result = db.get_table_dependencies(table_name)
            
            if result["success"]:
                output = f"✅ Dependencies for table '{table_name}':\n\n"
                
                # Tables this table depends on
                depends_on = result.get("depends_on", [])
                if depends_on:
                    output += f"📤 This table depends on:\n"
                    for dep in depends_on:
                        output += f"   • {dep['REFERENCED_TABLE_NAME']}.{dep['REFERENCED_COLUMN_NAME']} ← {dep['COLUMN_NAME']} ({dep['CONSTRAINT_NAME']})\n"
                else:
                    output += "📤 This table has no dependencies (no foreign keys)\n"
                
                output += "\n"
                
                # Tables that depend on this table
                referenced_by = result.get("referenced_by", [])
                if referenced_by:
                    output += f"📥 Tables that depend on this table:\n"
                    for ref in referenced_by:
                        output += f"   • {ref['DEPENDENT_TABLE']}.{ref['DEPENDENT_COLUMN']} → {ref['REFERENCED_COLUMN_NAME']} ({ref['CONSTRAINT_NAME']})\n"
                else:
                    output += "📥 No tables depend on this table\n"
            else:
                error_msg = result.get('message') or result.get('error', 'Unknown error')
                output = f"❌ Dependencies query failed: {error_msg}"

            return {"content": [{"type": "text", "text": output}]}
        
        elif request.name == make_tool_name(TOOL_SCHEMA_SUMMARY):
            result = db.get_schema_summary()
            
            if result["success"]:
                output = "✅ Database Schema Summary:\n\n"
                
                summary = result.get("summary", [])
                for item in summary:
                    obj_type = item['OBJECT_TYPE']
                    count = item['COUNT']
                    
                    # Add appropriate emoji
                    emoji_map = {
                        'Tables': '📋',
                        'Views': '👁️',
                        'Stored Procedures': '⚙️',
                        'Functions': '🔧'
                    }
                    emoji = emoji_map.get(obj_type, '📄')

                    output += f"{emoji} {obj_type}: {count}\n"
            else:
                error_msg = result.get('message') or result.get('error', 'Unknown error')
                output = f"❌ Schema summary query failed: {error_msg}"

            return {"content": [{"type": "text", "text": output}]}
        
        elif request.name == make_tool_name(TOOL_CACHE_STATS):
            result = db.get_cache_stats()
            
            if result["success"]:
                if result.get("cache_enabled", False):
                    output = "✅ Schema Cache Statistics:\n\n"
                    output += f"🔧 Cache Enabled: Yes\n"
                    output += f"📊 Cache Size: {result['cache_size']} entries\n"
                    output += f"⏱️ TTL: {result['cache_ttl_minutes']} minutes\n"
                    output += f"🚀 Preload Enabled: {'Yes' if result['preload_enabled'] else 'No'}\n\n"
                    
                    if result['cached_keys']:
                        output += f"🗂️ Cached Keys ({len(result['cached_keys'])}):\n"
                        for key in result['cached_keys']:
                            output += f"   • {key}\n"
                    else:
                        output += "📭 No cached entries\n"
                else:
                    output = "ℹ️ Schema caching is not enabled"
            else:
                error_msg = result.get('message') or result.get('error', 'Unknown error')
                output = f"❌ Failed to get cache stats: {error_msg}"

            return {"content": [{"type": "text", "text": output}]}
        
        elif request.name == make_tool_name(TOOL_CACHE_INVALIDATE):
            table_name = request.arguments.get("table_name")
            result = db.invalidate_schema_cache(table_name)
            
            if result["success"]:
                if table_name:
                    output = f"✅ Cache invalidated for table: {table_name}"
                else:
                    output = "✅ All cache entries invalidated"
            else:
                error_msg = result.get('message') or result.get('error', 'Unknown error')
                output = f"❌ Cache invalidation failed: {error_msg}"
            
            return {"content": [{"type": "text", "text": output}]}
        
        elif request.name == make_tool_name(TOOL_SCHEMA_RELOAD):
            result = db.reload_schema_config()
            
            if result["success"]:
                output = "✅ Schema configuration reloaded successfully\n"
                output += "🔄 Schemas have been re-preloaded from configuration"
            else:
                error_msg = result.get('message') or result.get('error', 'Unknown error')
                output = f"❌ Schema reload failed: {error_msg}"
            
            return {"content": [{"type": "text", "text": output}]}
        
        elif request.name == make_tool_name(TOOL_STATIC_SCHEMA_INFO):
            try:
                # Check if static schema data is available in cache
                static_summary = db.schema_cache.get("schema_summary_static") if db.schema_cache else None
                static_overview = db.schema_cache.get("database_overview_static") if db.schema_cache else None
                
                if static_summary or static_overview:
                    output = "✅ Static Schema Files Status:\n\n"
                    
                    if static_summary:
                        summary_data = static_summary.get("summary", [])
                        output += "📊 Static Schema Summary:\n"
                        for item in summary_data:
                            output += f"   • {item['OBJECT_TYPE']}: {item['COUNT']}\n"
                        output += "\n"
                    
                    if static_overview:
                        tables = static_overview.get("results", [])
                        output += f"📋 Static Tables ({len(tables)}):\n"
                        for table in tables[:MAX_TABLES_PREVIEW]:  # Show first MAX_TABLES_PREVIEW tables
                            source = table.get('FILE_SOURCE', 'unknown')
                            output += f"   • {table['TABLE_NAME']} (from {source})\n"

                        if len(tables) > MAX_TABLES_PREVIEW:
                            output += f"   ... and {len(tables) - MAX_TABLES_PREVIEW} more tables\n"
                    
                    output += "\n💡 Static schemas are loaded from JSON configuration system"
                    output += "\n🔄 They provide instant access without database queries"
                else:
                    output = "ℹ️ No static schema configurations detected\n"
                    output += "📁 Configure JSON schemas in the 'schemas_config/' directory to enable static preloading"
            except Exception as e:
                output = f"❌ Failed to get static schema info: {str(e)}"
            
            return {"content": [{"type": "text", "text": output}]}

        elif request.name == make_tool_name(TOOL_EXPORT_SCHEMA):
            table_name = request.arguments.get("table_name")
            output_dir = request.arguments.get("output_dir", "schema_export")
            include_business_logic = request.arguments.get("include_business_logic", True)

            if not table_name:
                return {
                    "content": [{"type": "text", "text": "❌ Error: table_name parameter is required"}]
                }

            try:
                # Import schema formatter here to avoid circular imports
                from database.schema.formatter import SchemaFormatter, BusinessLogicEnhancer

                # Get table schema information
                schema_result = db.get_schema_info(table_name)

                if not schema_result["success"]:
                    return {
                        "content": [{"type": "text", "text": f"❌ Failed to get schema for table '{table_name}': {schema_result.get('message', 'Unknown error')}"}]
                    }

                columns = schema_result.get("results", [])
                if not columns:
                    return {
                        "content": [{"type": "text", "text": f"❌ No columns found for table '{table_name}'"}]
                    }

                # Initialize formatter and enhancer
                formatter = SchemaFormatter()

                business_descriptions = {}
                if include_business_logic:
                    enhancer = BusinessLogicEnhancer()
                    business_descriptions = enhancer.enhance_column_descriptions(columns)

                # Format schema
                schema_content = formatter.format_table_schema(
                    table_name=table_name,
                    columns=columns,
                    business_descriptions=business_descriptions
                )

                # Save schema to file
                file_path = formatter.save_schema_to_file(
                    schema_content=schema_content,
                    table_name=table_name,
                    output_dir=output_dir
                )

                # Also generate table list with comments
                table_list_path = None
                table_list_error = None

                try:
                    table_list_result = db.get_schema_info()  # Get all tables

                    if table_list_result.get("success"):
                        tables = table_list_result.get("results", [])
                        if tables:
                            table_list_content = formatter.format_table_list(tables)
                            table_list_path = formatter.save_table_list_to_file(
                                table_list_content=table_list_content,
                                output_dir=output_dir
                            )
                        else:
                            table_list_error = "No tables found in database"
                    else:
                        table_list_error = table_list_result.get("error", "Failed to get schema info")
                except Exception as e:
                    table_list_error = f"Exception while generating table list: {str(e)}"

                output = f"✅ Schema exported successfully!\n\n"
                output += f"📋 Table: {table_name}\n"
                output += f"📁 Schema File: {file_path}\n"

                # Table list status
                if table_list_path:
                    output += f"📄 Table List: {table_list_path}\n"
                elif table_list_error:
                    output += f"⚠️  Table List: Failed to generate ({table_list_error})\n"
                else:
                    output += f"⚠️  Table List: Not generated (unknown reason)\n"

                output += f"📊 Columns: {len(columns)}\n"
                output += f"💼 Business Logic: {'Enabled' if include_business_logic else 'Disabled'}\n\n"
                output += "📄 Schema Preview:\n"
                output += "─" * 50 + "\n"
                output += schema_content[:400]  # Show first 400 characters
                if len(schema_content) > 400:
                    output += "\n... (truncated, see full content in file)"

                if table_list_path:
                    try:
                        tables_count = len(table_list_result.get("results", []))
                        output += "\n\n📋 Table List Generated:\n"
                        output += "─" * 30 + "\n"
                        output += f"包含 {tables_count} 個資料庫物件"
                    except:
                        output += "\n\n📋 Table List Generated Successfully"

                return {"content": [{"type": "text", "text": output}]}

            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"❌ Failed to export schema: {str(e)}"}]
                }

        elif request.name == make_tool_name(TOOL_SYNTAX_GUIDE):
            # Get dynamic table descriptions
            _tables_desc = get_key_tables_description()

            output = f"""🗄️  Database Type: Microsoft SQL Server (T-SQL)

📝 Date/Time Functions:
   • Current date/time: GETDATE()
   • Date parts: YEAR(date), MONTH(date), DAY(date)
   • Date arithmetic: DATEADD(day, 7, date), DATEDIFF(day, date1, date2)
   • Format: CONVERT(VARCHAR, date, 120)

📊 Query Syntax:
   • Limit rows: SELECT TOP 10 ...
   • String concat: col1 + col2 (or CONCAT(col1, col2))
   • Case-insensitive: Use COLLATE or default behavior

📋 {_tables_desc}

💡 Always use '{get_tool_prefix()}_schema' first to see exact table/column names!
"""

            return {"content": [{"type": "text", "text": output}]}

        else:
            return {
                "content": [{"type": "text", "text":f"❌ Unknown tool: {request.name}"}]
            }
    
    except Exception as e:
        logger.error(f"Tool call error in {request.name}: {e}", exc_info=True)
        
        # Enhanced error information for debugging
        error_output = f"❌ Internal server error in tool '{request.name}'\n\n"
        error_output += f"Error: {str(e)}\n"
        error_output += f"Error Type: {type(e).__name__}\n\n"
        error_output += "💡 This appears to be a server-side issue. Please check:\n"
        error_output += "   • Database connectivity\n"
        error_output += "   • Tool parameters and syntax\n"
        error_output += "   • Server logs for detailed error information\n"
        
        return {
            "content": [{"type": "text", "text": error_output}]
        }


async def main():
    """Main server entry point."""
    # Create MCP server
    server_name = os.getenv("MCP_SERVER_NAME", "mcp-db")
    server = Server(server_name)
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """Return available tools."""
        return TOOLS_DEFINITIONS
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Optional[dict] = None) -> dict:
        """Handle tool calls."""
        # Create CallToolRequest-like object from parameters
        request = type('CallToolRequest', (), {
            'name': name,
            'arguments': arguments or {}
        })()
        return await handle_call_tool(request)
    
    @server.list_prompts()
    async def list_prompts() -> List[Prompt]:
        """Return available prompts."""
        return []
    
    @server.list_resources()
    async def list_resources() -> List[Resource]:
        """Return available resources."""
        return []
    
    # Run server
    logger.info(f"🚀 Starting MCP Database Server ({server_name})...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())