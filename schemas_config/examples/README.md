# Schema Configuration Examples

This directory contains example configuration files to help you set up `schemas_config/` for your own database.

## Files

- **`sample_table.json`** - A complete table configuration example showing all available fields and formats. Use this as a reference when creating your own `tables/*.json` files.

## How to Use

1. Copy `sample_table.json` to `../tables/YOUR_TABLE.json`
2. Replace the table name, columns, relationships, and business logic with your own
3. Register the table in `../tables_list.json` under the `tables` key
4. Restart the MCP server or HTTP API to load the new configuration

## Minimal Configuration

You don't need all fields. A minimal table config only requires:

```json
{
  "table_name": "YOUR_TABLE",
  "display_name": "Your Table",
  "key_columns": {
    "ID": {
      "semantic_type": "primary_identifier",
      "description": "Primary key"
    }
  }
}
```

The system will automatically apply `global_patterns.json` rules for any columns not explicitly defined.
