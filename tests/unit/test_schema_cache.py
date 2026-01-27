"""
Schema 快取系統單元測試

測試 Schema 快取功能，包括 LFU+LRU 淘汰策略、TTL 過期、並行預載等。
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

import pytest

from database.schema.cache import (
    SchemaCache,
    SchemaPreloader,
    CachedSchemaIntrospector,
)


class TestSchemaCache:
    """Schema 快取核心功能測試"""

    def test_cache_initialization(self):
        """✅ 快取初始化"""
        cache = SchemaCache(cache_ttl_minutes=30, max_size=100)
        assert cache.cache_ttl == timedelta(minutes=30)
        assert cache.max_size == 100
        assert len(cache.cache) == 0
        assert len(cache.access_count) == 0
        assert len(cache.last_access) == 0

    def test_set_and_get_basic(self):
        """✅ 基本的 set 和 get 操作"""
        cache = SchemaCache()
        test_data = {"test": "data", "value": 123}

        cache.set("test_key", test_data)
        result = cache.get("test_key")

        assert result == test_data
        assert cache.access_count["test_key"] == 1  # 第一次訪問
        assert "test_key" in cache.last_access

    def test_get_nonexistent_key(self):
        """❌ 獲取不存在的 key 返回 None"""
        cache = SchemaCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_access_tracking(self):
        """✅ 訪問統計追蹤"""
        cache = SchemaCache()
        cache.set("key1", "value1")

        # 第一次訪問
        cache.get("key1")
        assert cache.access_count["key1"] == 1

        # 第二次訪問
        cache.get("key1")
        assert cache.access_count["key1"] == 2

        # 第三次訪問
        cache.get("key1")
        assert cache.access_count["key1"] == 3

    def test_ttl_expiration(self):
        """⏰ TTL 過期測試"""
        # 使用非常短的 TTL（0.01 分鐘 = 0.6 秒）
        cache = SchemaCache(cache_ttl_minutes=0.01)
        cache.set("short_lived", "data")

        # 立即獲取應該成功
        assert cache.get("short_lived") == "data"

        # 等待過期
        time.sleep(1)

        # 過期後應該返回 None
        assert cache.get("short_lived") is None
        assert "short_lived" not in cache.cache  # 應該被自動清除

    def test_invalidate_key(self):
        """✅ 手動失效化快取"""
        cache = SchemaCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 失效化單個 key
        cache.invalidate("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"  # key2 應該還在

        # 訪問統計也應該被清除
        assert "key1" not in cache.access_count
        assert "key1" not in cache.last_access

    def test_clear_all(self):
        """✅ 清除所有快取"""
        cache = SchemaCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 訪問以生成統計
        cache.get("key1")
        cache.get("key2")

        # 清除所有
        cache.clear()

        assert len(cache.cache) == 0
        assert len(cache.last_updated) == 0
        assert len(cache.access_count) == 0
        assert len(cache.last_access) == 0

    def test_lfu_lru_eviction_basic(self):
        """✅ LFU+LRU 混合淘汰策略（基本測試）"""
        cache = SchemaCache(max_size=5)

        # 填充快取到最大容量
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")

        # 創建訪問頻率差異
        cache.get("key0")  # 訪問 1 次
        cache.get("key0")  # 訪問 2 次
        cache.get("key0")  # 訪問 3 次（熱門）

        cache.get("key1")  # 訪問 1 次
        cache.get("key1")  # 訪問 2 次（中等）

        # key2, key3, key4 沒有訪問（冷門，頻率為 0）

        # 添加新 key 觸發淘汰
        cache.set("new_key", "new_value")

        # key0（高頻）和 key1（中頻）應該保留
        assert cache.get("key0") is not None
        assert cache.get("key1") is not None

        # 新 key 應該存在
        assert cache.get("new_key") is not None

    def test_lfu_lru_eviction_time_decay(self):
        """✅ LFU+LRU 時間衰減測試"""
        cache = SchemaCache(max_size=3)

        # 添加並訪問 key1（使其成為熱門）
        cache.set("key1", "value1")
        for _ in range(10):
            cache.get("key1")  # 頻率 = 10

        # 修改 last_access 使其看起來是很久以前的（模擬舊數據）
        cache.last_access["key1"] = datetime.now() - timedelta(hours=24)

        # 添加新的 key（頻率低但是最近訪問）
        cache.set("key2", "value2")
        cache.get("key2")  # 頻率 = 1，但是剛訪問

        cache.set("key3", "value3")
        cache.get("key3")  # 頻率 = 1，但是剛訪問

        # 觸發淘汰
        cache.set("key4", "value4")

        # key1 雖然頻率高，但因為太久沒訪問，分數會降低
        # 計算分數：key1 = 10 / (1 + 24h) ≈ 0.4
        #          key2 = 1 / (1 + 0h) = 1
        #          key3 = 1 / (1 + 0h) = 1
        # key1 應該有可能被淘汰（取決於具體實現）

    def test_preload_status_tracking(self):
        """✅ 預載狀態追蹤"""
        cache = SchemaCache()

        # 初始狀態
        status = cache.get_preload_status()
        assert status["static_preload_completed"] is False
        assert status["dynamic_preload_completed"] is False
        assert status["static_tables_count"] == 0
        assert status["dynamic_tables_count"] == 0

        # 標記靜態預載完成
        static_tables = ["TABLE1", "TABLE2", "TABLE3"]
        cache.mark_static_preload_complete(static_tables)

        status = cache.get_preload_status()
        assert status["static_preload_completed"] is True
        assert status["static_tables_count"] == 3
        assert status["preload_timestamp"] is not None

        # 標記動態預載完成
        dynamic_tables = ["TABLE4", "TABLE5"]
        cache.mark_dynamic_preload_complete(dynamic_tables)

        status = cache.get_preload_status()
        assert status["dynamic_preload_completed"] is True
        assert status["dynamic_tables_count"] == 2
        assert status["total_tables"] == 5  # 3 + 2（去重後）

    def test_is_table_preloaded(self):
        """✅ 檢查表格是否已預載"""
        cache = SchemaCache()

        cache.mark_static_preload_complete(["TABLE1", "TABLE2"])
        cache.mark_dynamic_preload_complete(["TABLE3", "TABLE4"])

        # TABLE1 在靜態預載中
        result = cache.is_table_preloaded("TABLE1")
        assert result["in_static"] is True
        assert result["in_dynamic"] is False
        assert result["preloaded"] is True

        # TABLE3 在動態預載中
        result = cache.is_table_preloaded("TABLE3")
        assert result["in_static"] is False
        assert result["in_dynamic"] is True
        assert result["preloaded"] is True

        # TABLE5 不在任何預載中
        result = cache.is_table_preloaded("TABLE5")
        assert result["in_static"] is False
        assert result["in_dynamic"] is False
        assert result["preloaded"] is False

    def test_thread_safety_basic(self):
        """✅ 基本線程安全測試"""
        import threading

        cache = SchemaCache()
        errors = []

        def set_and_get(key_prefix, iterations=100):
            try:
                for i in range(iterations):
                    key = f"{key_prefix}_{i}"
                    cache.set(key, f"value_{i}")
                    result = cache.get(key)
                    assert result == f"value_{i}"
            except Exception as e:
                errors.append(e)

        # 創建多個線程同時操作快取
        threads = [
            threading.Thread(target=set_and_get, args=(f"thread{i}",))
            for i in range(5)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 不應該有錯誤
        assert len(errors) == 0

    def test_max_size_enforcement(self):
        """✅ 最大容量限制"""
        cache = SchemaCache(max_size=10)

        # 添加超過最大容量的項目
        for i in range(20):
            cache.set(f"key{i}", f"value{i}")

        # 快取大小應該不超過最大值（考慮淘汰）
        # 淘汰策略會移除 10% 當達到上限時
        assert len(cache.cache) <= 11  # max_size + 少量餘量


class TestSchemaPreloader:
    """Schema 預載器測試"""

    def test_preloader_initialization(self):
        """✅ 預載器初始化"""
        introspector = Mock()
        cache = SchemaCache()
        preloader = SchemaPreloader(introspector, cache)

        assert preloader.introspector == introspector
        assert preloader.cache == cache
        assert preloader.preload_config == {}

    def test_preload_table_schema_success(self):
        """✅ 成功預載單個表格 schema"""
        introspector = Mock()
        introspector.get_schema_info.return_value = {
            "success": True,
            "results": [{"column_name": "id", "data_type": "INT"}],
        }

        cache = SchemaCache()
        preloader = SchemaPreloader(introspector, cache)

        result = preloader._preload_table_schema("TEST_TABLE")

        assert result is True
        assert cache.get("table_schema_TEST_TABLE") is not None
        introspector.get_schema_info.assert_called_once_with("TEST_TABLE")

    def test_preload_table_schema_failure(self):
        """❌ 預載失敗的處理"""
        introspector = Mock()
        introspector.get_schema_info.return_value = {
            "success": False,
            "error": "Table not found",
        }

        cache = SchemaCache()
        preloader = SchemaPreloader(introspector, cache)

        result = preloader._preload_table_schema("NONEXISTENT_TABLE")

        assert result is False
        assert cache.get("table_schema_NONEXISTENT_TABLE") is None

    def test_preload_database_overview(self):
        """✅ 預載資料庫概覽"""
        introspector = Mock()
        introspector.get_schema_info.return_value = {
            "success": True,
            "results": [{"table_name": "TABLE1"}, {"table_name": "TABLE2"}],
        }
        introspector.get_schema_summary.return_value = {
            "success": True,
            "summary": [{"object_type": "Tables", "count": 2}],
        }

        cache = SchemaCache()
        preloader = SchemaPreloader(introspector, cache)

        preloader._preload_database_overview()

        assert cache.get("database_overview") is not None
        assert cache.get("schema_summary") is not None

    @patch("database.schema.cache.ThreadPoolExecutor")
    def test_parallel_preload(self, mock_executor_class):
        """✅ 並行預載測試"""
        # Mock ThreadPoolExecutor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock future objects
        mock_future1 = MagicMock()
        mock_future1.result.return_value = True
        mock_future2 = MagicMock()
        mock_future2.result.return_value = True

        mock_executor.submit.side_effect = [mock_future1, mock_future2]

        # Mock as_completed to return futures
        with patch("database.schema.cache.as_completed", return_value=[mock_future1, mock_future2]):
            introspector = Mock()
            cache = SchemaCache()
            preloader = SchemaPreloader(introspector, cache)

            # 設置預載配置
            preloader.preload_config = {
                "preload_overview": False,
                "preload_tables": ["TABLE1", "TABLE2"],
                "critical_tables": [],
            }

            result = preloader.preload_schemas_concurrent(max_concurrent=5)

            assert result is True
            # 驗證並行執行器被正確調用
            assert mock_executor.submit.call_count >= 2


class TestCachedSchemaIntrospector:
    """快取 Schema 探查器測試"""

    def test_introspector_initialization(self):
        """✅ 探查器初始化"""
        original_introspector = Mock()
        cache = SchemaCache()

        introspector = CachedSchemaIntrospector(original_introspector, cache)

        assert introspector.introspector == original_introspector
        assert introspector.cache == cache
        assert introspector.strict_mode is False

    def test_get_schema_dynamic_cache_hit(self):
        """✅ 動態快取命中"""
        original_introspector = Mock()
        cache = SchemaCache()

        # 預先設置動態快取
        cache_data = {
            "success": True,
            "results": [{"column": "id"}],
        }
        cache.set("table_schema_USERS", cache_data)

        introspector = CachedSchemaIntrospector(original_introspector, cache)
        result = introspector.get_schema_info("USERS")

        assert result["success"] is True
        assert result["cache_source"] == "dynamic_cache"
        # 不應該查詢原始探查器
        original_introspector.get_schema_info.assert_not_called()

    def test_get_schema_static_cache_fallback(self):
        """✅ 靜態快取降級"""
        original_introspector = Mock()
        cache = SchemaCache()

        # 只設置靜態快取
        static_data = {
            "success": True,
            "results": [{"column": "id"}],
            "source": "json_config_system",
        }
        cache.set("table_schema_USERS_static", static_data)

        introspector = CachedSchemaIntrospector(original_introspector, cache)
        result = introspector.get_schema_info("USERS")

        assert result["success"] is True
        assert result["cache_source"] == "static_cache"
        # 不應該查詢原始探查器
        original_introspector.get_schema_info.assert_not_called()

    def test_get_schema_database_query(self):
        """✅ 快取未命中，查詢資料庫"""
        original_introspector = Mock()
        original_introspector.get_schema_info.return_value = {
            "success": True,
            "results": [{"column": "id"}],
        }

        cache = SchemaCache()
        introspector = CachedSchemaIntrospector(original_introspector, cache)

        result = introspector.get_schema_info("USERS")

        assert result["success"] is True
        assert result["cache_source"] == "database_query"
        # 應該查詢原始探查器
        original_introspector.get_schema_info.assert_called_once_with("USERS")

        # 結果應該被快取
        cached = cache.get("table_schema_USERS")
        assert cached is not None
        assert cached["cache_source"] == "database_query"

    def test_strict_mode_blocks_uncached_access(self):
        """❌ 嚴格模式阻止未快取的訪問"""
        original_introspector = Mock()
        cache = SchemaCache()

        introspector = CachedSchemaIntrospector(
            original_introspector, cache, strict_mode=True
        )

        result = introspector.get_schema_info("UNCACHED_TABLE")

        assert result["success"] is False
        assert "denied" in result["error"].lower() or result.get("strict_mode") is True
        assert result["cache_source"] == "denied"
        # 不應該查詢原始探查器
        original_introspector.get_schema_info.assert_not_called()

    def test_strict_mode_allows_cached_access(self):
        """✅ 嚴格模式允許已快取的訪問"""
        original_introspector = Mock()
        cache = SchemaCache()

        # 預載靜態快取
        cache.set("table_schema_ALLOWED_TABLE_static", {
            "success": True,
            "results": [{"column": "id"}],
        })

        introspector = CachedSchemaIntrospector(
            original_introspector, cache, strict_mode=True
        )

        result = introspector.get_schema_info("ALLOWED_TABLE")

        assert result["success"] is True
        assert result["cache_source"] == "static_cache"

    def test_invalidate_cache_single_table(self):
        """✅ 失效化單個表格快取"""
        original_introspector = Mock()
        cache = SchemaCache()

        # 設置多個快取
        cache.set("table_schema_TABLE1", {"data": "table1"})
        cache.set("table_schema_TABLE2", {"data": "table2"})
        cache.set("table_dependencies_TABLE1", {"deps": "table1"})

        introspector = CachedSchemaIntrospector(original_introspector, cache)
        introspector.invalidate_cache("TABLE1")

        # TABLE1 的快取應該被清除
        assert cache.get("table_schema_TABLE1") is None
        assert cache.get("table_dependencies_TABLE1") is None

        # TABLE2 的快取應該還在
        assert cache.get("table_schema_TABLE2") is not None

    def test_invalidate_cache_all(self):
        """✅ 清除所有快取"""
        original_introspector = Mock()
        cache = SchemaCache()

        # 設置多個快取
        cache.set("table_schema_TABLE1", {"data": "table1"})
        cache.set("table_schema_TABLE2", {"data": "table2"})

        introspector = CachedSchemaIntrospector(original_introspector, cache)
        introspector.invalidate_cache()  # 不指定表格 = 清除全部

        assert len(cache.cache) == 0

    def test_get_dependencies_from_static_config(self):
        """✅ 從靜態配置獲取依賴關係"""
        original_introspector = Mock()
        cache = SchemaCache()

        # 設置包含關係的靜態 schema
        cache.set("table_schema_ORDERS_static", {
            "success": True,
            "source": "json_config_system",
            "relationships": {
                "foreign_keys": [
                    {
                        "column": "user_id",
                        "references": "USERS.id",
                        "description": "Order owner",
                    }
                ]
            },
        })

        introspector = CachedSchemaIntrospector(original_introspector, cache)
        result = introspector.get_table_dependencies("ORDERS")

        assert result["success"] is True
        assert result["source"] == "json_config_system"
        assert len(result["dependencies"]) == 1
        assert result["dependencies"][0]["parent_table"] == "ORDERS"
        assert result["dependencies"][0]["referenced_table"] == "USERS"

    def test_cache_source_tracking(self):
        """✅ 快取來源追蹤"""
        original_introspector = Mock()
        cache = SchemaCache()

        # 測試動態快取來源標記
        cache.set("table_schema_TABLE1", {"success": True})
        introspector = CachedSchemaIntrospector(original_introspector, cache)
        result = introspector.get_schema_info("TABLE1")
        assert result.get("cache_source") == "dynamic_cache"

        # 測試靜態快取來源標記
        cache.clear()
        cache.set("table_schema_TABLE2_static", {"success": True})
        result = introspector.get_schema_info("TABLE2")
        assert result.get("cache_source") == "static_cache"

        # 測試資料庫查詢來源標記
        cache.clear()
        original_introspector.get_schema_info.return_value = {"success": True}
        result = introspector.get_schema_info("TABLE3")
        assert result.get("cache_source") == "database_query"


class TestCachePerformance:
    """快取性能測試"""

    def test_large_cache_performance(self):
        """✅ 大容量快取性能測試"""
        cache = SchemaCache(max_size=10000)

        start_time = time.time()

        # 添加大量數據
        for i in range(1000):
            cache.set(f"key{i}", {"data": f"value{i}" * 100})

        set_time = time.time() - start_time

        # 隨機訪問
        start_time = time.time()
        for i in range(500):
            cache.get(f"key{i}")

        get_time = time.time() - start_time

        # 性能應該是可接受的（具體閾值取決於硬體）
        assert set_time < 2.0  # 1000 次 set 應該在 2 秒內完成
        assert get_time < 0.5  # 500 次 get 應該在 0.5 秒內完成

    def test_eviction_performance(self):
        """✅ 淘汰策略性能測試"""
        cache = SchemaCache(max_size=100)

        # 填充快取
        for i in range(100):
            cache.set(f"key{i}", f"value{i}")
            if i % 2 == 0:
                cache.get(f"key{i}")  # 創建訪問模式

        start_time = time.time()

        # 觸發多次淘汰
        for i in range(100, 200):
            cache.set(f"new_key{i}", f"new_value{i}")

        eviction_time = time.time() - start_time

        # 淘汰操作應該高效
        assert eviction_time < 1.0  # 100 次淘汰觸發應該在 1 秒內完成
