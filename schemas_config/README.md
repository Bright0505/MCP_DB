# Schema Configuration System v2.1 - User Manual

## Overview

This system uses pure JSON configuration with a three-layer knowledge injection architecture to manage database table and column semantic definitions, helping AI accurately understand your business logic.

## Quick Start

### Step 1: Understand the File Structure
```
schemas_config/
├── tables_list.json          # [Required] Table whitelist and global settings
├── global_patterns.json      # [Required] Global column patterns and reusable logic
├── ai_enhancement.json       # [Required] AI query enhancement settings
├── examples/                 # Reference examples
│   └── sample_table.json     # Complete table config example
└── tables/                   # [Optional] Individual table detailed configs
    └── .gitkeep
```

### Step 2: Minimal Configuration (Get Started)
1. **Ensure required files exist**: `tables_list.json`, `global_patterns.json`, `ai_enhancement.json`
2. **Register your tables in `tables_list.json`**:
   ```json
   {
     "tables": {
       "YOUR_TABLE": {"table_type": "TABLE", "display_name": "Your Table Name"}
     }
   }
   ```
3. **The system will automatically apply `global_patterns.json` naming rules**

### Step 3: Add Detailed Configs for Important Tables (Optional)
For Critical/High importance tables, create `tables/YOUR_TABLE.json`:
```json
{
  "table_name": "YOUR_TABLE",
  "display_name": "Your Table Name",
  "business_logic": {
    "primary_date_field": "DATE_COLUMN",
    "primary_amount_field": "AMOUNT_COLUMN"
  },
  "key_columns": {
    "ID": {"semantic_type": "primary_identifier", "description": "Primary key"}
  }
}
```

See `examples/sample_table.json` for a complete reference.

### Step 4: Test Your Configuration
1. Restart the MCP server or HTTP API
2. Use `get_cached_schema` tool to verify Schema is loaded correctly
3. Test AI queries to confirm your configuration is understood

## System Architecture

### Three-Layer Schema Architecture

This system uses a **whitelist + enhancement configuration** layered design:

#### Layer 1: Whitelist Layer (tables_list.json)
- **Purpose**: Define all accessible tables
- **Required**: Yes - all accessible tables must be registered here
- **Content**: Basic info (table_type, display_name)
- **Access Control**: Only tables defined here can be accessed by the system

#### Layer 2: Detailed Config Layer (tables/*.json)
- **Purpose**: Provide detailed metadata for important tables
- **Required**: Optional - only for Critical/High importance tables
- **Content**: columns, relationships, business_logic, ai_context

#### Layer 3: Global Pattern Layer (global_patterns.json + ai_enhancement.json)
- **global_patterns.json**: Common column naming patterns (e.g., `_ID$`, `_DATE$`)
- **ai_enhancement.json**: Natural language query mappings and patterns

### Loading Logic and Strict Mode

**Loading order** (highest to lowest priority):
1. `tables/*.json` (Detailed config layer)
2. `tables_list.json` (Whitelist layer)
3. `global_patterns.json` (Global patterns)

**Strict Mode behavior**:
- `SCHEMA_STRICT_MODE=true` (default): Only allows access to tables in `tables_list.json`
- `SCHEMA_STRICT_MODE=false`: Allows dynamic database schema queries on cache miss

## Configuration File Reference

### 1. tables_list.json
Defines basic info, categories, and importance levels for all tables.

### 2. global_patterns.json
Defines reusable column naming rules and calculation formulas. Time patterns include both SQL Server and PostgreSQL syntax using `{date_column}` placeholders.

### 3. ai_enhancement.json
Defines natural language to SQL mappings for AI query optimization.

### 4. tables/*.json
Per-table detailed configuration. See `examples/sample_table.json` for a complete reference.

## Semantic Types (semantic_type) Reference

| Type | Description | Example | Usage |
|------|-------------|---------|-------|
| `primary_identifier` | Primary key | ORDER_ID | Unique identifier for the table |
| `foreign_key` | Foreign key | CUSTOMER_ID | References another table |
| `primary_date` | Primary date | ORDER_DATE | Most important time field |
| `primary_amount` | Primary amount | TOTAL_AMOUNT | Most important monetary field |
| `status` | Status | STATUS | Record state (active/cancelled etc.) |
| `money` | Amount | PRICE | General monetary field |
| `quantity` | Quantity | QTY | Quantity-related field |
| `datetime` | Date/Time | CREATE_DATE | General date/time field |
| `code` | Code | DEPT_CODE | Code classification field |
| `identifier` | Identifier | PROD_ID | General identifier (non-PK) |
| `name` | Name | PROD_NAME | Display name field |
| `category` | Category | TYPE, KIND | Classification field |

## Maintenance Guide

- **Add a table**: Update `tables_list.json`. For important tables, also create `tables/<TABLE>.json`.
- **New naming pattern**: Update `global_patterns.json` if multiple tables share column naming conventions.
- **New query scenario**: Update `ai_enhancement.json` to support new natural language keywords.
- **Validate configs**: After changes, verify JSON syntax and test AI query understanding.

## Validation and Testing

### JSON Syntax Validation
```bash
for file in schemas_config/*.json schemas_config/tables/*.json; do
  python -m json.tool "$file" > /dev/null && echo "OK: $file"
done
```

### Schema Load Test
```python
from src.database.schema.static_loader import get_cached_schema
schema = get_cached_schema("YOUR_TABLE")
print(schema)
```

## FAQ

- **Q: Config not taking effect?** Check JSON syntax, file paths, and restart the service.
- **Q: Do I need tables/*.json for every table?** No, only for Critical/High importance tables. Others use global_patterns.
- **Q: How to add a new table?** Add it to `tables_list.json` under `tables`. Optionally create `tables/{TABLE}.json`.
