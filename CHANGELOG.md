# 更新日誌

本文件記錄 MCP Multi-Database Connector 的所有重要變更。

## [v1.0.0] - 2026-01-28 - 初始版本

### 功能
- **多資料庫支援**：原生 SQL Server (MSSQL) 與 PostgreSQL 連接器
- **11 個 MCP 工具**：db_query、db_schema、db_schema_summary、db_dependencies、db_test_connection、db_cache_stats、db_cache_invalidate、db_schema_reload、db_static_schema_info、db_export_schema、db_syntax_guide
- **雙模式架構**：Claude Desktop (MCP stdio) + HTTP API (FastAPI + OpenAPI)
- **靜態 Schema 預載**：透過 `schemas_config/` JSON 配置注入業務語義
- **三層知識注入**：tables_list.json（白名單）→ tables/*.json（詳細配置）→ global_patterns.json（全域模式）
- **智慧快取系統**：LFU + LRU + TTL 多層快取
- **AI 增強**：Schema 感知查詢、Token 優化（60-80% 節省）、SQL 語法導引
- **SQL 安全驗證**：唯讀模式，僅允許 SELECT 查詢
- **Docker 部署**：docker-compose 一鍵啟動

### 技術
- 分層模組化架構：core → database → tools → server/http_server
- 完整單元測試：101 個測試（100% 通過率）
- 非同步資料庫管理器（AsyncDatabaseManager）
- 可配置工具前綴（TOOL_PREFIX 環境變數，預設 `db`）
