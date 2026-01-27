# MCP Quick Start Guide

## What is MCP?

**Model Context Protocol (MCP)** is an open protocol by Anthropic that allows AI assistants to securely connect to external data sources and tools.

This project implements a full MCP server with **10+ database tools**, enabling Claude to directly access and analyze your database.

**Security**: The server uses **read-only mode** by default, supporting only SELECT queries.

---

## ✨ 核心功能

### 🔌 連線管理
- `db_test_connection` - 測試資料庫連線狀態

### 📊 資料查詢（只讀模式）
- `db_query` - 執行 SELECT 查詢並返回結果（不支援 INSERT/UPDATE/DELETE）

### 🗄️ Schema 分析
- `db_schema` - 查看資料庫表格和欄位結構
- `db_dependencies` - 分析表格間的依賴關係
- `db_schema_summary` - 查看資料庫摘要統計
- `db_export_schema` - 匯出表格 Schema 到文件
- `db_static_schema_info` - 查看靜態 Schema 配置資訊

### ⚡ 效能優化
- `db_cache_stats` - 查看 Schema 快取統計資訊
- `db_cache_invalidate` - 清除快取條目
- `db_schema_reload` - 重新載入 Schema 配置

---

## 🎯 使用方式

### 方法 1: Claude Desktop 整合 (推薦)

#### 步驟 1: 準備環境

```bash
# 克隆專案
git clone https://github.com/yourusername/mcp-db.git
cd mcp-db

# 配置環境變數
cp .env.example .env
# 編輯 .env 填入您的資料庫連線資訊

# 安裝依賴 (如果使用本地模式)
pip install -e .
```

#### 步驟 2: 配置 Claude Desktop

找到您的 Claude Desktop 配置檔案:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

複製專案根目錄的 `claude_desktop_config.example.json` 內容並修改路徑:

```json
{
  "mcpServers": {
    "mcp-db": {
      "command": "python",
      "args": ["-m", "server"],
      "cwd": "/path/to/mcp-db",
      "env": {
        "DB_TYPE": "mssql",
        "DB_HOST": "localhost",
        "DB_NAME": "your_database",
        "DB_USER": "your_username",
        "DB_PASSWORD": "your_password",
        "DB_PORT": "1433",
        "SCHEMA_ENABLE_CACHE": "true"
      }
    }
  }
}
```

#### 步驟 3: 重啟 Claude Desktop

完全關閉並重新啟動 Claude Desktop 應用程式。

#### 步驟 4: 測試整合

在 Claude Desktop 中輸入:

```
請測試資料庫連線狀態
```

如果看到連線成功的訊息,表示整合完成!

---

### 方法 2: Docker 模式 (推薦開發環境)

#### 步驟 1: 啟動 Docker 容器

```bash
# 配置環境變數
cp .env.example .env
# 編輯 .env

# 啟動容器
docker-compose up -d mcp-db
```

#### 步驟 2: 配置 Claude Desktop (Docker 模式)

```json
{
  "mcpServers": {
    "mcp-db": {
      "command": "docker",
      "args": [
        "exec", "-i", "mcp-db-dev",
        "python", "-m", "server"
      ]
    }
  }
}
```

#### 步驟 3: 驗證容器運行

```bash
# 檢查容器狀態
docker ps | grep mcp-db

# 查看日誌
docker logs mcp-db-dev --tail 20
```

---

### 方法 3: HTTP API 模式 (適用 Open WebUI)

#### 啟動 HTTP 伺服器

```bash
# Docker 模式
docker-compose up -d mcp-db-http

# 本地模式
python -m http_server
```

#### 存取 API

- API 端點: `http://localhost:8000`
- API 文檔: `http://localhost:8000/docs`

#### 範例請求

```bash
# 測試連線
curl -X POST http://localhost:8000/api/test-connection

# 執行查詢
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT TOP 10 * FROM users"}'

# 查看 Schema
curl -X POST http://localhost:8000/api/schema \
  -H "Content-Type: application/json" \
  -d '{"table_name": "users"}'
```

---

## 💬 Claude Desktop 使用範例

### 1. 基本查詢

```
Claude, 請幫我查詢資料庫中有多少個用戶?
```

### 2. Complex Analysis

```
Analyze the past 30 days by product category,
including total revenue and order count, sorted by revenue descending
```

### 3. Schema Exploration

```
Show all database tables and describe their purpose
```

### 4. Dependency Analysis

```
Analyze the orders table dependencies,
including tables it depends on and tables that depend on it
```

### 5. Data Validation

```
Check the users table for duplicate email addresses
```

### 6. Schema Export

```
Export the complete Schema for the products table to a file
```

---

## 🔧 進階配置

### 啟用 Schema 快取 (推薦)

在 `.env` 或 Claude Desktop 配置中添加:

```env
SCHEMA_ENABLE_CACHE=true
SCHEMA_CACHE_TTL_MINUTES=60
SCHEMA_PRELOAD_ON_STARTUP=true
```

**好處**:
- ⚡ 快取系統提供毫秒級回應速度
- 💾 減少資料庫查詢次數
- 🚀 預載重要表格的 Schema

### 多資料庫支援

您可以在 Claude Desktop 中配置多個資料庫連線:

```json
{
  "mcpServers": {
    "mcp-production": {
      "command": "python",
      "args": ["-m", "server"],
      "env": {
        "DB_HOST": "prod-server",
        "DB_NAME": "production_db"
      }
    },
    "mcp-staging": {
      "command": "python",
      "args": ["-m", "server"],
      "env": {
        "DB_HOST": "staging-server",
        "DB_NAME": "staging_db"
      }
    }
  }
}
```

### PostgreSQL 配置範例

```json
{
  "mcpServers": {
    "mcp-postgres": {
      "command": "python",
      "args": ["-m", "server"],
      "env": {
        "DB_TYPE": "postgresql",
        "DB_HOST": "localhost",
        "DB_NAME": "mydb",
        "DB_USER": "postgres",
        "DB_PASSWORD": "password",
        "DB_PORT": "5432",
        "DB_SCHEMA": "public",
        "DB_SSLMODE": "prefer"
      }
    }
  }
}
```

---

## 🔒 安全性建議

### 1. 使用只讀帳戶

建議為 Claude Desktop 配置只讀資料庫用戶:

**PostgreSQL**:
```sql
CREATE USER claude_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE your_database TO claude_readonly;
GRANT USAGE ON SCHEMA public TO claude_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_readonly;
```

**SQL Server**:
```sql
CREATE LOGIN claude_readonly WITH PASSWORD = 'secure_password';
USE your_database;
CREATE USER claude_readonly FOR LOGIN claude_readonly;
ALTER ROLE db_datareader ADD MEMBER claude_readonly;
```

### 2. 環境變數管理

- ❌ **不要** 將密碼直接寫在配置檔案中
- ✅ **建議** 使用系統環境變數
- ✅ **建議** 使用 `.env` 檔案並加入 `.gitignore`

### 3. 敏感資料保護

- 避免查詢包含個人隱私的敏感資料
- 定期審核資料庫存取日誌
- 限制查詢結果數量 (使用 LIMIT/TOP)

---

## 🐛 故障排除

### ❌ Claude Desktop 沒有顯示 MCP 工具

**檢查項目**:
1. 配置檔案語法是否正確 (JSON 格式)
2. Python 路徑是否正確
3. 專案路徑 (cwd) 是否正確
4. 是否已重啟 Claude Desktop

**驗證方法**:
```bash
# 檢查 JSON 語法
cat claude_desktop_config.json | python -m json.tool

# 測試 MCP 伺服器
cd /path/to/mcp-db
python -m server
```

### ❌ 資料庫連線失敗

**檢查項目**:
1. 資料庫服務是否運行
2. 網路連線是否正常
3. 用戶名密碼是否正確
4. 防火牆是否阻擋連線

**測試連線**:
```bash
# 測試網路
ping your-db-host

# 測試端口
telnet your-db-host 1433

# 測試資料庫連線
python -c "
from database import DatabaseManager
from config import DatabaseConfig
config = DatabaseConfig.from_env()
db = DatabaseManager(config)
print(db.test_connection())
"
```

### ❌ Docker 容器無法啟動

**檢查項目**:
```bash
# 查看容器狀態
docker ps -a | grep mcp-db

# 查看容器日誌
docker logs mcp-db-dev

# 重啟容器
docker-compose restart mcp-db

# 重新建置
docker-compose build mcp-db
docker-compose up -d mcp-db
```

---

## 其他資源

- [安裝指南](installation.md)
- [系統架構](architecture.md)
- [Schema 系統](schema-system.md)
- [效能優化](performance.md)
- [測試指南](testing.md)

---

**版本**：v5.0.0
**最後更新**：2026-01-27
