# 測試指南

## 📋 概述

MCP Multi-Database Connector 提供完整的測試套件，包括單元測試和整合測試，確保所有核心功能穩定可靠。

## 🧪 測試架構

### 測試類型

```
tests/
├── unit/                  # 單元測試（101 個測試）
│   ├── test_validators.py        # SQL 驗證器測試（50 個）
│   ├── test_schema_cache.py      # Schema 快取測試（29 個）
│   └── test_async_manager.py     # 異步管理器測試（22 個）
└── integration/           # 整合測試（28 個測試）
    └── test_api_endpoints.py     # HTTP API 端點測試
```

## ✅ 單元測試

### 測試統計

| 指標 | 數值 |
|------|------|
| 總測試數 | 101 |
| 通過率 | 100% |
| 執行時間 | ~1.8 秒 |
| 總體覆蓋率 | 27% |

### 關鍵模組覆蓋率

| 模組 | 覆蓋率 | 評級 |
|------|--------|------|
| `tools/validators.py` | 96% | ⭐⭐⭐ 優秀 |
| `database/async_manager.py` | 88% | ⭐⭐⭐ 優秀 |
| `core/exceptions.py` | 79% | ⭐⭐ 良好 |
| `tools/base.py` | 73% | ⭐⭐ 良好 |
| `database/schema/static_loader.py` | 69% | ⭐ 及格 |
| `core/config.py` | 66% | ⭐ 及格 |
| `database/schema/cache.py` | 64% | ⭐ 及格 |

### 測試模組說明

#### 1. test_validators.py (50 個測試)
**覆蓋率**: 96%

測試 SQL 安全驗證功能：
- SQL 注入防護（31 個測試）
- 輸入驗證（15 個測試）
- 安全邊緣案例（4 個測試）

**關鍵測試**：
- 阻止危險 SQL 語句（DELETE, DROP, EXEC 等）
- SQL 注入攻擊防護（UNION, 註解等）
- 輸入長度和格式驗證

#### 2. test_schema_cache.py (29 個測試)
**覆蓋率**: 64%

測試 Schema 快取系統：
- 基本快取操作（設定、取得、失效）
- LFU+LRU 淘汰策略
- TTL 過期機制
- 並行預載
- 靜態 Schema 載入

**關鍵測試**：
- 快取命中/未命中
- 多層快取查詢（靜態→動態→資料庫）
- 線程安全性
- 性能測試

#### 3. test_async_manager.py (22 個測試)
**覆蓋率**: 88%

測試異步資料庫管理：
- 異步連接池
- 並發查詢執行
- 錯誤處理
- 敏感資訊保護

**關鍵測試**：
- 連接池重用
- 並發查詢執行
- 連接失敗處理
- 查詢錯誤處理

## 🚀 執行測試

### 在 Docker 容器中執行

```bash
# 執行所有單元測試
docker exec mcp-db-http-dev pytest /app/tests/unit/ -v

# 執行特定測試文件
docker exec mcp-db-http-dev pytest /app/tests/unit/test_validators.py -v

# 執行帶覆蓋率報告的測試
docker exec mcp-db-http-dev pytest /app/tests/unit/ \
  --cov=/app/src \
  --cov-report=term \
  --cov-report=html

# 查看 HTML 覆蓋率報告
# 報告位置：/app/htmlcov/index.html
```

### 本地執行（需配置環境）

```bash
# 安裝測試依賴
pip install pytest pytest-asyncio pytest-cov

# 執行測試
pytest tests/unit/ -v

# 執行帶覆蓋率報告
pytest tests/unit/ --cov=src --cov-report=html
```

## 🔧 配置說明

### pytest 配置

測試配置位於 `pyproject.toml`：

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

這個配置確保異步測試正常運行。

### 必要依賴

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
]
```

## 📊 測試覆蓋重點

### ✅ 完全覆蓋
- SQL 注入防護
- 輸入驗證
- 異步查詢執行
- 連接池管理
- 敏感資訊保護

### ⚠️ 部分覆蓋
- Schema 快取系統
- LFU+LRU 淘汰策略
- 靜態 Schema 載入器
- 資料庫配置管理

### ❌ 未覆蓋（未來改進）
- HTTP API 層（需整合測試）
- MCP 伺服器核心協議
- SSE/Stdio 傳輸層
- Schema 格式化器
- Tool Handlers

## 🎯 測試最佳實踐

### 1. 測試命名規範

```python
def test_valid_simple_select():          # ✅ 清晰的測試名稱
    """測試簡單的 SELECT 查詢驗證"""
    pass

def test_reject_delete_query():         # ✅ 清晰描述預期行為
    """測試拒絕 DELETE 語句"""
    pass
```

### 2. 使用 Fixtures

```python
@pytest.fixture
def mock_db_manager():
    """Mock 資料庫管理器"""
    manager = Mock()
    manager.test_connection.return_value = {"success": True}
    return manager
```

### 3. 異步測試

```python
@pytest.mark.asyncio
async def test_async_function():
    """測試異步函數"""
    result = await some_async_function()
    assert result is not None
```

## 📈 CI/CD 整合

### GitHub Actions 範例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          pytest tests/unit/ \
            --cov=src \
            --cov-report=xml \
            --cov-fail-under=25
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 🐛 故障排除

### 常見問題

#### 1. 異步測試失敗

**問題**: `SyntaxError: 'await' outside async function`

**解決方案**:
```bash
# 確保已安裝 pytest-asyncio
pip install pytest-asyncio

# 檢查 pyproject.toml 配置
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

#### 2. 導入錯誤

**問題**: `ModuleNotFoundError: No module named 'src'`

**解決方案**:
```bash
# 在容器中執行測試
docker exec mcp-db-http-dev pytest /app/tests/unit/ -v

# 或設置 PYTHONPATH
export PYTHONPATH=/app/src
pytest tests/unit/ -v
```

#### 3. 資料庫連接失敗（整合測試）

**問題**: 整合測試需要真實資料庫連接

**解決方案**:
- 使用 Mock 物件進行單元測試
- 整合測試需要配置 .env 文件
- 或使用測試資料庫

## 📋 未來改進計劃

### 短期
- [ ] 提升 schema/cache.py 覆蓋率至 80%
- [ ] 修復整合測試（test_api_endpoints.py）
- [ ] 添加 Tool Handlers 單元測試

### 中期
- [ ] E2E 測試框架
- [ ] CI/CD 整合
- [ ] 性能基準測試

### 長期
- [ ] 負載測試
- [ ] 跨平台測試
- [ ] 覆蓋率監控儀表板

## 📚 參考資源

- [pytest 文檔](https://docs.pytest.org/)
- [pytest-asyncio 文檔](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov 文檔](https://pytest-cov.readthedocs.io/)

---

**MCP Multi-Database Connector 測試套件已建立完整的單元測試基礎，確保核心功能穩定可靠！**
