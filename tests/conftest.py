"""
pytest 配置文件

提供測試環境設定、fixtures 和全局配置
"""

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# 添加 src 目錄到 Python 路徑
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# 載入環境變數
load_dotenv()


@pytest.fixture(scope="session")
def test_config():
    """測試配置 fixture"""
    return {
        "db_type": "mssql",  # 或從環境變數讀取
        "max_query_length": 50000,
        "cache_ttl_minutes": 60,
        "max_concurrent_queries": 5,
    }


@pytest.fixture
def sample_query():
    """範例查詢 fixture"""
    return "SELECT TOP 10 name FROM sys.tables"


@pytest.fixture
def sample_malicious_queries():
    """惡意查詢範例 fixture（用於測試 SQL 注入防護）"""
    return [
        "SELECT * FROM users; DROP TABLE users;--",
        "SELECT * FROM users WHERE id = 1 OR 1=1--",
        "SELECT * FROM users/* comment */WHERE id=1",
        "SELECT * FROM OPENROWSET('SQLNCLI', 'Server=x;Trusted_Connection=yes;', 'SELECT * FROM sys.tables')",
        "DELETE FROM users WHERE id = 1",
        "DROP TABLE users",
        "UPDATE users SET password = 'hacked'",
        "EXEC sp_executesql N'SELECT * FROM users'",
    ]


@pytest.fixture
def sample_table_name():
    """範例表格名稱 fixture"""
    return "SALE00"
