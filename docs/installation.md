# 📦 安裝指南

本指南將幫助您在不同環境中安裝和設定 MCP Multi-Database Connector。選擇適合您需求的安裝方式。

## 📋 系統需求

### 最低需求
- **Python**: 3.8 或更高版本
- **記憶體**: 1GB RAM
- **硬碟**: 500MB 可用空間
- **網路**: 可存取資料庫伺服器

### 建議需求
- **Python**: 3.10 或更高版本
- **記憶體**: 2GB RAM 或更多
- **硬碟**: 2GB 可用空間
- **CPU**: 2 核心或更多

### 支援的作業系統
- ✅ **Windows** 10/11
- ✅ **macOS** 10.15 (Catalina) 或更新
- ✅ **Linux** (Ubuntu 18.04+, CentOS 7+, 其他主流發行版)

---

## 🎯 選擇安裝方式

| 安裝方式 | 適合對象 | 複雜度 | 隔離性 |
|----------|----------|--------|--------|
| 🐍 **Python pip** | 開發者、本地使用 | 🟢 簡單 | 🟡 中等 |
| 🐳 **Docker** | 生產環境、多服務 | 🟡 中等 | 🟢 完全隔離 |
| 📦 **從原始碼** | 貢獻者、自訂需求 | 🔴 進階 | 🟡 中等 |

---

## 方式 1: 🐍 Python pip 安裝 (推薦)

### 步驟 1: 檢查 Python 版本
```bash
python --version
# 應該顯示 Python 3.8.0 或更高版本

# 如果您的系統同時有 Python 2 和 3
python3 --version
```

### 步驟 2: 建立虛擬環境 (強烈建議)
```bash
# 創建虛擬環境
python -m venv mcp-db-env

# 啟動虛擬環境
# Windows
mcp-db-env\Scripts\activate

# macOS/Linux
source mcp-db-env/bin/activate
```

### 步驟 3: 克隆專案
```bash
# 使用 git 克隆
git clone https://github.com/brightsu/mcp-db.git
cd mcp-db

# 或下載 ZIP 檔案
# 從 GitHub 下載並解壓到本地目錄
```

### 步驟 4: 安裝依賴
```bash
# 安裝專案 (開發模式)
pip install -e .

# 或安裝開發工具
pip install -e ".[dev]"        # 包含開發工具
```

### 步驟 5: 驗證安裝
```bash
# 測試 MCP 服務器
python -m server --help

# 測試 HTTP API
python -m http_server --help

# 測試 Python 模組
python -c "import server; print('安裝成功!')"
```

---

## 方式 2: 🐳 Docker 安裝

### 前置需求
確保已安裝 Docker 和 Docker Compose：
```bash
# 檢查 Docker
docker --version

# 檢查 Docker Compose
docker-compose --version
```

### 步驟 1: 下載專案
```bash
git clone https://github.com/brightsu/mcp-db.git
cd mcp-db
```

### 步驟 2: 配置環境變數
```bash
# 複製環境變數範本
cp .env.example .env

# 編輯配置 (請參考配置指南)
nano .env
```

### 步驟 3: 建立映像檔
```bash
# 建立 Docker 映像檔
docker-compose build

# 或拉取預建映像檔 (如果可用)
docker-compose pull
```

### 步驟 4: 啟動服務
```bash
# 啟動所有服務
docker-compose up -d

# 檢查服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f
```

### 步驟 5: 驗證安裝
```bash
# 檢查容器狀態
docker ps | grep mcp-db

# 測試 HTTP API
curl http://localhost:8000/docs

# 測試 MCP 服務器
docker exec -it mcp-db-dev python -m server --help
```

---

## 方式 3: 📦 從原始碼安裝

### 步驟 1: 安裝開發工具
```bash
# 安裝 git
# Windows: 從 git-scm.com 下載
# macOS: xcode-select --install
# Linux: sudo apt-get install git

# 安裝 Python 開發環境
# 建議使用 pyenv 管理 Python 版本
```

### 步驟 2: 克隆並設定開發環境
```bash
# 克隆專案
git clone https://github.com/brightsu/mcp-db.git
cd mcp-db

# 創建開發環境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安裝開發依賴
pip install -e ".[dev]"
```

### 步驟 3: 安裝額外工具
```bash
# 安裝代碼品質工具
pip install black isort mypy pytest

# 安裝 pre-commit hooks
pre-commit install
```

### 步驟 4: 執行測試
```bash
# 執行單元測試
pytest tests/

# 執行代碼檢查
black --check src/
isort --check-only src/
mypy src/
```

---

## 🗄️ 資料庫驅動程式安裝

### SQL Server (ODBC Driver)

**Windows**:
```bash
# 通常已預裝，如需更新：
# 從 Microsoft 官網下載 ODBC Driver 18 for SQL Server
```

**macOS**:
```bash
# 使用 Homebrew
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
brew install msodbcsql18 mssqltools18
```

**Linux (Ubuntu/Debian)**:
```bash
# 添加 Microsoft 套件來源
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/20.04/prod focal main" > /etc/apt/sources.list.d/mssql-release.list

# 安裝驅動程式
sudo apt-get update
ACCEPT_EULA=Y sudo apt-get install msodbcsql18
```

**驗證安裝**:
```bash
# 檢查已安裝的 ODBC 驅動程式
odbcinst -q -d
```

### PostgreSQL (psycopg2)

PostgreSQL 驅動程式通常會自動隨 pip 安裝一起安裝，但如果遇到問題：

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install libpq-dev python3-dev

# CentOS/RHEL
sudo yum install postgresql-devel python3-devel
```

**macOS**:
```bash
# 使用 Homebrew
brew install postgresql
```

**Windows**:
```bash
# 通常會自動安裝，如有問題可安裝 PostgreSQL 官方套件
```

---

## ⚙️ 環境配置

### 步驟 1: 創建配置檔案
```bash
# 複製範本
cp .env.example .env
```

### 步驟 2: 基本配置
```bash
# 編輯 .env 檔案
nano .env
```

**最小配置範例**:
```bash
# 資料庫類型選擇
DB_TYPE=postgresql  # 或 mssql

# 資料庫連線
DB_HOST=localhost
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_PORT=5432  # PostgreSQL: 5432, SQL Server: 1433
```

詳細配置選項請參考 [.env.example](../.env.example)。

---

## 🧪 安裝驗證

### 基本功能測試
```bash
# 測試 Python 模組導入
python -c "
import server
from database import DatabaseManager
from schema import SchemaIntrospector
print('✅ 所有模組載入成功')
"

# 測試配置載入
python -c "
from config import DatabaseConfig
config = DatabaseConfig.from_env()
print(f'✅ 配置載入成功: {config.db_type}')
"
```

### 連線測試
```bash
# 使用內建測試工具
python -c "
from database import DatabaseManager
from config import DatabaseConfig
config = DatabaseConfig.from_env()
db = DatabaseManager(config)
result = db.test_connection()
print(f'連線測試結果: {result}')
"
```

### 服務測試
```bash
# 測試 MCP 服務器
python -m server --help && echo "✅ MCP 服務器正常"

# 測試 HTTP API 啟動
python -m http_server &
sleep 3
curl -f http://localhost:8000/docs && echo "✅ HTTP API 服務正常"
```

---

## 🔧 故障排除

### 常見安裝問題

**❌ Python 版本過舊**
```bash
# 解決方案：升級 Python
# 使用 pyenv (推薦)
curl https://pyenv.run | bash
pyenv install 3.10.0
pyenv global 3.10.0
```

**❌ pip 安裝失敗**
```bash
# 更新 pip
python -m pip install --upgrade pip

# 清除快取
pip cache purge

# 使用不同來源
pip install -i https://pypi.org/simple/ -e .
```

**❌ ODBC 驅動程式問題**
```bash
# 檢查驅動程式
odbcinst -q -d

# 重新安裝 (macOS)
brew uninstall msodbcsql18
brew install msodbcsql18
```

**❌ Docker 權限問題**
```bash
# Linux: 將用戶加入 docker 群組
sudo usermod -aG docker $USER
newgrp docker
```

### 獲得幫助

如果安裝過程中遇到問題：

- [GitHub Issues](https://github.com/Bright0505/MCP_DB/issues) — 搜尋已知問題或回報新問題

---

## 下一步

安裝完成後，建議：

1. [快速開始](quick-start.md) — 5 分鐘上手指南
2. [MCP 快速入門](MCP_QUICK_START.md) — Claude Desktop 整合
3. [schemas_config 配置](../schemas_config/README.md) — 業務客製化

---

**版本**：v1.0.0
**最後更新**：2026-01-27