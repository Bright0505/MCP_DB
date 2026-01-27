# MCP Multi-Database Connector

[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![Database](https://img.shields.io/badge/database-SQL%20Server%20%7C%20PostgreSQL-orange.svg)](https://github.com/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

A Model Context Protocol (MCP) server template providing multi-database integration. Supports Microsoft SQL Server and PostgreSQL with static Schema preloading and intelligent analysis. Use `schemas_config/` to customize for your specific business domain.

## Features

### Core
- **Multi-database support**: Native SQL Server and PostgreSQL connectors
- **10+ database tools**: Query, execute, Schema analysis, dependency analysis
- **Static Schema preloading**: Built-in JSON config parser for business metadata
- **Intelligent caching**: Configurable TTL cache with millisecond Schema responses
- **Relationship analysis**: Table dependency and foreign key analysis

### AI-Powered
- **Schema-aware AI**: Generates precise SQL based on actual database structure and business metadata
- **Token optimization**: 60-80% token savings through Schema compression
- **SQL optimization**: AI-driven query performance analysis

### Dual-Mode Architecture
- **Claude Desktop (MCP Protocol)**: Full MCP tool support via stdio
- **Open WebUI (HTTP API)**: RESTful API + OpenAPI/Swagger documentation

## Quick Start

### Mode 1: Claude Desktop (MCP Protocol)
```bash
# 1. Copy example config
cp claude_desktop_config.example.json ~/.config/Claude/claude_desktop_config.json

# 2. Edit config: set project path and database connection info
# 3. Restart Claude Desktop

# Detailed steps: docs/MCP_QUICK_START.md
```

### Mode 2: Open WebUI (HTTP API)
```bash
# 1. Install dependencies
pip install -e .

# 2. Configure connection
cp .env.example .env
# Edit .env with your database info

# 3. Start HTTP API server
python -m http_server

# 4. API docs at http://localhost:8000/docs
```

## Docker Deployment

```bash
# Start all services
docker-compose up -d

# Services:
# - MCP Server: stdio mode (Claude Desktop)
# - HTTP API: http://localhost:8000 (Open WebUI)
```

## Configuration

```bash
# Basic settings
DB_TYPE=postgresql  # or mssql
DB_HOST=your_server_address
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password

# Schema cache (recommended)
SCHEMA_ENABLE_CACHE=true
SCHEMA_CACHE_TTL_MINUTES=60

# HTTP API
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
```

## MCP Tools

- **query_database**: Execute SQL SELECT queries
- **list_tables**: List all tables
- **get_table_schema**: Get table Schema information
- **get_database_info**: View database statistics
- **get_table_relationships**: Analyze table relationships
- **execute_sql**: Execute DML/DDL statements
- **get_cached_schema**: Get cached Schema
- **export_schema**: Export Schema configuration
- **analyze_query**: SQL query analysis
- **clear_cache**: Clear Schema cache

## Customizing for Your Business

This project is a **template** designed to be customized via `schemas_config/`:

### Three-Layer Knowledge Injection

1. **Global patterns** (`global_patterns.json`) - Automatic column name pattern recognition (e.g., `_ID$`, `_DATE$`, `_AMT$`)
2. **Table business logic** (`tables/*.json`) - Detailed column descriptions, status value definitions, JOIN suggestions
3. **AI enhancement** (`ai_enhancement.json`) - Natural language keyword mappings, query pattern templates

### Getting Started with Customization

1. Register your tables in `schemas_config/tables_list.json`
2. Add detailed configs for important tables in `schemas_config/tables/`
3. Configure AI query patterns in `schemas_config/ai_enhancement.json`
4. See `schemas_config/examples/sample_table.json` for a complete reference

Detailed guide: [schemas_config/README.md](schemas_config/README.md)

## Documentation

### Getting Started
- [MCP Quick Start](docs/MCP_QUICK_START.md) - MCP feature guide (recommended)
- [Installation Guide](docs/installation.md) - Setup and environment
- [Configuration Guide](docs/configuration.md) - Configuration options
- [Quick Start](docs/quick-start.md) - 5-minute guide

### Usage
- [Claude Desktop Integration](docs/claude-desktop.md) - Claude Desktop setup
- [HTTP API Usage](docs/http-api.md) - REST API endpoints and examples

### Technical
- [System Architecture](docs/architecture.md) - Design and modules
- [Schema System](docs/schema-system.md) - Static Schema and JSON config
- [Performance](docs/performance.md) - Caching and token optimization
- [Multi-Database Support](docs/database-support.md) - SQL Server and PostgreSQL

### Development
- [Development Environment](docs/development/README.md) - Setup and contribution guide
- [Docker Deployment](docs/docker.md) - Container deployment guide
- [Testing Guide](docs/testing.md) - Unit tests and coverage
- [API Reference](docs/api-reference.md) - Complete API docs
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## License

MIT License - see [LICENSE](LICENSE)

---

**Version**: v5.0.0
**Last Updated**: 2026-01-27
