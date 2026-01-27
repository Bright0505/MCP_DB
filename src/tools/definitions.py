"""MCP tool definitions for Multi-Database Connector."""

import json
import os
from pathlib import Path
from typing import List, Optional
from mcp.types import Tool


def get_tool_prefix() -> str:
    """Get tool name prefix from environment or default."""
    return os.getenv("TOOL_PREFIX", "posdb")


def make_tool_name(suffix: str) -> str:
    """Generate a tool name with the configured prefix.

    Args:
        suffix: The tool suffix (e.g. 'query', 'schema')

    Returns:
        Full tool name (e.g. 'posdb_query')
    """
    return f"{get_tool_prefix()}_{suffix}"


# Tool suffix constants (used for matching in handlers)
TOOL_QUERY = "query"
TOOL_SCHEMA = "schema"
TOOL_TEST_CONNECTION = "test_connection"
TOOL_DEPENDENCIES = "dependencies"
TOOL_SCHEMA_SUMMARY = "schema_summary"
TOOL_CACHE_STATS = "cache_stats"
TOOL_CACHE_INVALIDATE = "cache_invalidate"
TOOL_SCHEMA_RELOAD = "schema_reload"
TOOL_STATIC_SCHEMA_INFO = "static_schema_info"
TOOL_EXPORT_SCHEMA = "export_schema"
TOOL_SYNTAX_GUIDE = "syntax_guide"


def get_key_tables_description() -> str:
    """Get key table descriptions from schemas_config/tables_list.json.

    Returns:
        str: Description string of key tables, or fallback message
    """
    prefix = get_tool_prefix()
    try:
        tables_list_path = Path(__file__).parent.parent.parent / "schemas_config" / "tables_list.json"
        if tables_list_path.exists():
            with open(tables_list_path, encoding='utf-8') as f:
                tables_data = json.load(f)

            critical_tables = tables_data.get("importance_levels", {}).get("critical", {}).get("tables", [])

            if critical_tables:
                tables_info = tables_data.get("tables", {})
                table_descriptions = []

                for table_name in critical_tables[:5]:
                    table_info = tables_info.get(table_name, {})
                    display_name = table_info.get("display_name", "")
                    if display_name:
                        table_descriptions.append(f"{table_name} ({display_name})")
                    else:
                        table_descriptions.append(table_name)

                if table_descriptions:
                    return "Key tables: " + ", ".join(table_descriptions) + ", etc."
    except Exception:
        pass

    return f"Use {prefix}_schema_summary to discover available tables."


def get_all_tools() -> List[Tool]:
    """Generate all MCP tool definitions with the configured prefix.

    Returns:
        List of Tool objects with prefixed names
    """
    prefix = get_tool_prefix()
    _key_tables_desc = get_key_tables_description()

    return [
        Tool(
            name=f"{prefix}_{TOOL_QUERY}",
            description=(
                "Execute a SELECT query on the database and return results. "
                "READ-ONLY: Only SELECT queries are supported. "
                "\n\n"
                "IMPORTANT: Before querying, use '"
                f"{prefix}_{TOOL_SCHEMA}' or '{prefix}_{TOOL_SCHEMA_SUMMARY}' "
                "to discover available tables and columns. Do NOT guess table names. "
                f"{_key_tables_desc}"
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
            name=f"{prefix}_{TOOL_SCHEMA}",
            description=(
                "Get detailed database schema information. "
                "USE THIS FIRST before writing queries to discover available tables and their structure. "
                "\n"
                f"Provide 'table_name' for specific table details, or omit it to list all available tables. "
                f"{_key_tables_desc}"
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
            name=f"{prefix}_{TOOL_TEST_CONNECTION}",
            description="Test the connection to database",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name=f"{prefix}_{TOOL_DEPENDENCIES}",
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
            name=f"{prefix}_{TOOL_SCHEMA_SUMMARY}",
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
            name=f"{prefix}_{TOOL_CACHE_STATS}",
            description="Get schema cache statistics and configuration",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name=f"{prefix}_{TOOL_CACHE_INVALIDATE}",
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
            name=f"{prefix}_{TOOL_SCHEMA_RELOAD}",
            description="Reload schema configuration and re-preload schemas",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name=f"{prefix}_{TOOL_STATIC_SCHEMA_INFO}",
            description="Get information about static schema files",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name=f"{prefix}_{TOOL_EXPORT_SCHEMA}",
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
            name=f"{prefix}_{TOOL_SYNTAX_GUIDE}",
            description=(
                "Get SQL syntax reference and common query patterns for this database. "
                "Use this to learn the correct syntax before writing queries."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


# Backward-compatible exports
POSDB_TOOLS = get_all_tools()
