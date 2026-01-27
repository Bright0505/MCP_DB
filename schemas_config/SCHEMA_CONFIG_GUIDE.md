# Schema Configuration System - Complete Guide

> This guide provides in-depth step-by-step instructions for mastering the Schema configuration system.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Three-Layer Architecture](#three-layer-architecture)
3. [Complete Configuration Workflow](#complete-configuration-workflow)
4. [Advanced Techniques](#advanced-techniques)
5. [Performance Optimization](#performance-optimization)
6. [Troubleshooting](#troubleshooting)

---

## Core Concepts

### Why Schema Configuration?

Database schemas only contain technical information (table names, column names, data types), but lack business semantics:

```sql
-- AI cannot understand the business meaning from technical schema alone
CREATE TABLE orders (
  order_id int,
  order_date timestamp,
  total_amount decimal(10,2),
  status varchar(20)
);
```

Problems:
- What is `order_id`? Only known as integer, format and purpose unclear
- What do `status` values represent?
- Which fields are most important? Which date field for time queries?

**Schema configuration solves this**:

```json
{
  "key_columns": {
    "ORDER_ID": {
      "semantic_type": "primary_identifier",
      "description": "Order number",
      "usage_notes": "Format: YYYYMMDD-NNNNNN"
    },
    "STATUS": {
      "semantic_type": "status",
      "enum_values": {"pending": "Pending", "confirmed": "Confirmed", "cancelled": "Cancelled"},
      "ai_hints": "Filter with STATUS != 'cancelled' for active orders"
    }
  }
}
```

Now AI can:
- Understand ORDER_ID is the primary key for joins
- Know STATUS='cancelled' records should be excluded
- Automatically use the correct fields for queries

---

## Three-Layer Architecture

### Architecture Overview

This system uses a **whitelist + enhancement configuration** three-layer architecture:

1. **Whitelist Layer (tables_list.json)**: Define all accessible tables
2. **Detailed Config Layer (tables/*.json)**: Provide detailed metadata for important tables
3. **Global Pattern Layer (global_patterns.json)**: Define reusable column rules

**Key Design Principles**:
- All tables must be registered in `tables_list.json` to be accessible
- Tables without detailed config (empty columns) can still be accessed for basic info
- Strict Mode prevents access to unregistered tables

### Layer 1: Whitelist Layer (tables_list.json)

**Purpose**: Access control and basic information.

**Required**: All accessible tables must be registered here.

```json
{
  "tables": {
    "ORDERS": {"table_type": "TABLE", "display_name": "Orders"},
    "CUSTOMERS": {"table_type": "TABLE", "display_name": "Customers"}
  }
}
```

**Strict Mode behavior**:
- In whitelist -> access allowed
- Not in whitelist -> access denied
- In whitelist but no detailed config -> basic info accessible

### Layer 2: Detailed Config Layer (tables/*.json)

**Purpose**: Provide detailed business logic and metadata for important tables.

**Required**: Optional - recommended only for Critical/High importance tables.

```json
{
  "table_name": "ORDERS",
  "columns": [{"COLUMN_NAME": "ORDER_ID", "description": "Order number"}],
  "relationships": {"foreign_keys": [...]},
  "business_logic": {"primary_key": "ORDER_ID"}
}
```

### Layer 3: Global Pattern Layer

**Purpose**: Define reusable naming rules to reduce repetitive configuration.

#### How It Works

The system uses regex patterns to match column names:

```json
{
  "column_patterns": {
    "_ID$": {
      "semantic_type": "identifier",
      "default_description": "Identifier"
    }
  }
}
```

Matching examples:
- `ORDER_ID` -> matches
- `CUSTOMER_ID` -> matches
- `ID_NUMBER` -> does not match (not at end)

#### When to Use Global Patterns

**Use when**:
- Multiple tables share the same column naming conventions
- Standardized terminology (e.g., all `_ID` columns are identifiers)
- Reducing maintenance cost of repetitive configs

**Don't use when**:
- Table-specific business logic (use tables/*.json)
- Same column name but different meaning across tables (override in tables/*.json)

### Field Priority Order

When the same column is defined in multiple places:

```
tables/*.json > global_patterns.json > database schema
```

---

## Complete Configuration Workflow

### Example: Setting Up an E-Commerce Order System

#### Step 1: Assess Requirements

**System description**:
- 3 tables: ORDERS (order header), ORDER_ITEMS (line items), CUSTOMERS
- Importance: ORDERS and ORDER_ITEMS are Critical, CUSTOMERS is High

#### Step 2: Create Directory Structure

```bash
mkdir -p schemas_config/tables
```

#### Step 3: Configure tables_list.json

```json
{
  "schema_version": "2.1",
  "loading_strategy": {
    "priority_order": ["table_json_config", "global_patterns"]
  },
  "table_categories": {
    "order_data": {
      "display_name": "Order Data",
      "description": "Order transaction data",
      "tables": ["ORDERS", "ORDER_ITEMS"]
    },
    "master_data": {
      "display_name": "Master Data",
      "description": "Core reference data",
      "tables": ["CUSTOMERS"]
    }
  },
  "importance_levels": {
    "critical": {"tables": ["ORDERS", "ORDER_ITEMS"]},
    "high": {"tables": ["CUSTOMERS"]}
  },
  "tables": {
    "ORDERS": {"table_type": "TABLE", "display_name": "Orders"},
    "ORDER_ITEMS": {"table_type": "TABLE", "display_name": "Order Items"},
    "CUSTOMERS": {"table_type": "TABLE", "display_name": "Customers"}
  }
}
```

#### Step 4: Create Detailed Table Config

Create `schemas_config/tables/ORDERS.json` (see `examples/sample_table.json` for a complete reference):

```json
{
  "table_name": "ORDERS",
  "display_name": "Orders",
  "business_importance": "critical",
  "business_logic": {
    "primary_date_field": "ORDER_DATE",
    "primary_amount_field": "TOTAL_AMOUNT",
    "status_field": "STATUS",
    "status_values": {
      "pending": "Pending",
      "confirmed": "Confirmed",
      "shipped": "Shipped",
      "cancelled": "Cancelled"
    },
    "active_records_filter": "STATUS NOT IN ('cancelled')"
  },
  "relationships": {
    "primary_key": ["ORDER_ID"],
    "foreign_keys": [
      {"column": "CUSTOMER_ID", "references": "CUSTOMERS.CUSTOMER_ID"}
    ]
  },
  "key_columns": {
    "ORDER_ID": {"semantic_type": "primary_identifier", "description": "Order ID"},
    "ORDER_DATE": {"semantic_type": "primary_date", "description": "Order date"},
    "TOTAL_AMOUNT": {"semantic_type": "primary_amount", "description": "Total amount"}
  }
}
```

#### Step 5: Configure AI Enhancement

```json
{
  "query_patterns": {
    "order_analysis": {
      "keywords": ["order", "purchase", "revenue"],
      "primary_tables": ["ORDERS", "ORDER_ITEMS"],
      "sample_queries": ["Today's order summary", "Top selling products"]
    }
  },
  "natural_language_mappings": {
    "chinese_keywords": {
      "today": "DATE(ORDER_DATE) = CURRENT_DATE",
      "this_month": "DATE_TRUNC('month', ORDER_DATE) = DATE_TRUNC('month', CURRENT_DATE)"
    }
  }
}
```

#### Step 6: Test Configuration

```bash
# 1. Validate JSON syntax
for f in schemas_config/*.json schemas_config/tables/*.json; do
  python -m json.tool "$f" > /dev/null && echo "OK: $f"
done

# 2. Restart service
docker-compose restart mcp-db-http

# 3. Test schema loading
curl http://localhost:8000/api/schema/ORDERS
```

---

## Advanced Techniques

### 1. Calculated Fields

```json
{
  "calculated_fields": {
    "net_revenue": {
      "formula": "TOTAL_AMOUNT - DISCOUNT",
      "description": "Net revenue",
      "sql_template": "(COALESCE(TOTAL_AMOUNT, 0) - COALESCE(DISCOUNT, 0))"
    }
  }
}
```

### 2. Timezone Handling

```json
{
  "metadata": {
    "timezone": "UTC",
    "utc_offset": "+00:00"
  },
  "key_columns": {
    "ORDER_DATE": {
      "semantic_type": "primary_date",
      "timezone_aware": true,
      "ai_hints": "Stored in UTC, convert for local time display"
    }
  }
}
```

### 3. SQL Server / PostgreSQL Dual Syntax

Use `{date_column}` placeholders in `global_patterns.json` time patterns. The system provides both SQL Server and PostgreSQL templates:

```json
{
  "time_patterns": {
    "current_month": {
      "sql_server": "MONTH({date_column}) = MONTH(GETDATE())",
      "postgresql": "DATE_TRUNC('month', {date_column}) = DATE_TRUNC('month', CURRENT_DATE)"
    }
  }
}
```

---

## Performance Optimization

### Cache Strategy

```env
SCHEMA_ENABLE_CACHE=true
SCHEMA_CACHE_TTL_MINUTES=60
```

**Cache levels**:
1. **Static JSON preload** (startup): Millisecond response
2. **Dynamic TTL cache** (runtime): Auto-refresh
3. **Database schema** (fallback): Real-time but slower

### Configuration File Size

- Only configure necessary fields - prioritize primary keys, foreign keys, dates, amounts
- Use `global_patterns` to avoid repetitive per-table definitions
- Keep descriptions concise

---

## Troubleshooting

### Problem 1: Configuration Not Taking Effect

```bash
# 1. Validate JSON syntax
python -m json.tool schemas_config/tables/YOUR_TABLE.json

# 2. Restart service
docker-compose restart mcp-db-http

# 3. Clear cache
curl -X POST http://localhost:8000/api/cache/clear
```

### Problem 2: AI Generates Incorrect SQL

1. **Check semantic_type** - ensure `primary_date` vs `datetime` is correct
2. **Check ai_hints** - provide clear filtering instructions
3. **Add natural language mappings** in `ai_enhancement.json`

### Problem 3: JSON Syntax Errors

Common mistakes:
- Missing comma between properties
- Trailing comma after last property
- Using single quotes (JSON requires double quotes)
- Using comments (JSON does not support comments)

Validation tools:
```bash
python -m json.tool file.json
jq . file.json
```

---

## Summary

### Best Practice Checklist

- [ ] All JSON files have correct syntax
- [ ] Critical/High tables have `tables/*.json` configs
- [ ] Key fields have `semantic_type` defined
- [ ] Business rules documented in `business_logic`
- [ ] Table relationships defined in `relationships`
- [ ] Natural language keywords mapped in `ai_enhancement.json`
- [ ] Cache enabled (`SCHEMA_ENABLE_CACHE=true`)
- [ ] Configuration tested with AI queries
