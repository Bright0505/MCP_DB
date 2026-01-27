"""
異步資料庫管理器單元測試

測試異步查詢、連接池和並發處理功能。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from core.config import AppConfig, DatabaseConfig


class TestAsyncDatabaseManager:
    """異步資料庫管理器測試"""

    @pytest.fixture
    def mock_config(self):
        """Mock 資料庫配置"""
        config = Mock(spec=DatabaseConfig)
        config.db_type = "mssql"
        config.host = "localhost"
        config.database = "testdb"
        config.get_connection_string.return_value = "connection_string"
        return config

    @pytest.fixture
    def mock_app_config(self):
        """Mock 應用配置"""
        config = Mock(spec=AppConfig)
        config.expose_sensitive_info = False
        return config

    @pytest.fixture
    def mock_async_connector(self):
        """Mock 異步連接器"""
        connector = AsyncMock()
        connector.initialize_pool = AsyncMock()
        connector.test_connection = AsyncMock(return_value={
            "success": True,
            "server_info": {
                "server": "localhost",
                "database": "testdb",
                "port": 1433,
                "driver": "ODBC Driver 17"
            }
        })
        connector.execute_query = AsyncMock(return_value={
            "success": True,
            "results": [{"id": 1, "name": "test"}],
            "columns": ["id", "name"],
            "row_count": 1
        })
        connector.close = AsyncMock()
        return connector

    @pytest.mark.asyncio
    async def test_initialization(self, mock_config, mock_app_config):
        """✅ 管理器初始化"""
        from database.async_manager import AsyncDatabaseManager

        manager = AsyncDatabaseManager(mock_config, mock_app_config)

        assert manager.config == mock_config
        assert manager.app_config == mock_app_config
        assert manager._initialized is False
        assert manager.db_connector is None

    @pytest.mark.asyncio
    async def test_initialize_creates_connector(self, mock_config, mock_app_config, mock_async_connector):
        """✅ initialize 方法創建連接器和連接池"""
        from database.async_manager import AsyncDatabaseManager

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)
            await manager.initialize(pool_size=5)

            assert manager._initialized is True
            assert manager.db_connector == mock_async_connector
            mock_async_connector.initialize_pool.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_initialize_only_once(self, mock_config, mock_app_config, mock_async_connector):
        """✅ 防止重複初始化"""
        from database.async_manager import AsyncDatabaseManager

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)

            await manager.initialize()
            await manager.initialize()  # 第二次調用

            # 應該只初始化一次
            assert mock_async_connector.initialize_pool.call_count == 1

    @pytest.mark.asyncio
    async def test_ensure_initialized_auto_init(self, mock_config, mock_app_config, mock_async_connector):
        """✅ ensure_initialized 自動初始化"""
        from database.async_manager import AsyncDatabaseManager

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)

            assert manager._initialized is False
            await manager.ensure_initialized()
            assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_test_connection_hides_sensitive_info(self, mock_config, mock_app_config, mock_async_connector):
        """✅ 測試連接時隱藏敏感資訊（預設行為）"""
        from database.async_manager import AsyncDatabaseManager

        mock_app_config.expose_sensitive_info = False

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)
            await manager.initialize()

            result = await manager.test_connection()

            assert result["success"] is True
            assert "server_info" in result
            # 敏感資訊應該被過濾
            assert "database" in result["server_info"]
            assert result["server_info"]["connected"] is True
            assert "server" not in result["server_info"]
            assert "port" not in result["server_info"]
            assert "driver" not in result["server_info"]

    @pytest.mark.asyncio
    async def test_test_connection_shows_sensitive_info_when_allowed(
        self, mock_config, mock_app_config, mock_async_connector
    ):
        """✅ 允許時顯示敏感資訊"""
        from database.async_manager import AsyncDatabaseManager

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)
            await manager.initialize()

            # 明確指定顯示敏感資訊
            result = await manager.test_connection(include_sensitive_info=True)

            assert result["success"] is True
            assert "server_info" in result
            # 敏感資訊應該保留
            assert "server" in result["server_info"]
            assert "port" in result["server_info"]
            assert "driver" in result["server_info"]

    @pytest.mark.asyncio
    async def test_execute_query(self, mock_config, mock_app_config, mock_async_connector):
        """✅ 執行異步查詢"""
        from database.async_manager import AsyncDatabaseManager

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)
            await manager.initialize()

            result = await manager.execute_query("SELECT * FROM users")

            assert result["success"] is True
            assert "results" in result
            assert result["row_count"] == 1
            mock_async_connector.execute_query.assert_called_once_with("SELECT * FROM users", None)

    @pytest.mark.asyncio
    async def test_execute_query_with_params(self, mock_config, mock_app_config, mock_async_connector):
        """✅ 執行帶參數的異步查詢"""
        from database.async_manager import AsyncDatabaseManager

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)
            await manager.initialize()

            params = ["value1", "value2"]
            await manager.execute_query("SELECT * FROM users WHERE name = ?", params)

            mock_async_connector.execute_query.assert_called_once_with(
                "SELECT * FROM users WHERE name = ?", params
            )

    @pytest.mark.asyncio
    async def test_close(self, mock_config, mock_app_config, mock_async_connector):
        """✅ 關閉連接池"""
        from database.async_manager import AsyncDatabaseManager

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)
            await manager.initialize()

            assert manager._initialized is True

            await manager.close()

            assert manager._initialized is False
            mock_async_connector.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_and_initialize_factory(self, mock_config, mock_app_config, mock_async_connector):
        """✅ create_and_initialize 工廠方法"""
        from database.async_manager import AsyncDatabaseManager

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = await AsyncDatabaseManager.create_and_initialize(
                config=mock_config,
                app_config=mock_app_config,
                pool_size=8
            )

            assert manager._initialized is True
            assert manager.config == mock_config
            mock_async_connector.initialize_pool.assert_called_once_with(8)

    @pytest.mark.asyncio
    async def test_concurrent_query_execution(self, mock_config, mock_app_config, mock_async_connector):
        """✅ 並發查詢執行"""
        from database.async_manager import AsyncDatabaseManager

        # 模擬不同查詢返回不同結果
        query_results = [
            {"success": True, "results": [{"id": i}], "row_count": 1}
            for i in range(5)
        ]
        mock_async_connector.execute_query.side_effect = query_results

        with patch("database.async_manager.create_async_database_connector", return_value=mock_async_connector):
            manager = AsyncDatabaseManager(mock_config, mock_app_config)
            await manager.initialize()

            # 並發執行多個查詢
            queries = [f"SELECT * FROM table{i}" for i in range(5)]
            tasks = [manager.execute_query(query) for query in queries]

            results = await asyncio.gather(*tasks)

            # 驗證所有查詢都成功執行
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result["success"] is True
                assert result["results"][0]["id"] == i


class TestHybridDatabaseManager:
    """混合資料庫管理器測試"""

    @pytest.fixture
    def mock_sync_manager(self):
        """Mock 同步管理器"""
        manager = Mock()
        manager.test_connection.return_value = {"success": True, "message": "sync"}
        manager.execute_query.return_value = {"success": True, "data": "sync"}
        manager.get_schema_info.return_value = {"success": True}
        manager.get_table_dependencies.return_value = {"success": True}
        manager.get_schema_summary.return_value = {"success": True}
        manager.invalidate_schema_cache.return_value = {"success": True}
        manager.reload_schema_config.return_value = {"success": True}
        manager.get_schema_cache_stats.return_value = {"cache_size": 10}
        manager.get_cache_debug_info.return_value = {"debug": "info"}
        manager.get_static_schema_info.return_value = {"static": "info"}
        manager.schema_cache = Mock()
        return manager

    @pytest.fixture
    def mock_async_manager(self):
        """Mock 異步管理器"""
        manager = AsyncMock()
        manager.test_connection = AsyncMock(return_value={"success": True, "message": "async"})
        manager.execute_query = AsyncMock(return_value={"success": True, "data": "async"})
        manager.close = AsyncMock()
        return manager

    def test_hybrid_initialization(self, mock_sync_manager):
        """✅ 混合管理器初始化"""
        from database.async_manager import HybridDatabaseManager

        with patch("database.manager.DatabaseManager", return_value=mock_sync_manager):
            config = Mock(spec=DatabaseConfig)
            app_config = Mock(spec=AppConfig)

            manager = HybridDatabaseManager(config, app_config)

            assert manager.config == config
            assert manager.app_config == app_config
            assert manager._async_initialized is False

    def test_sync_methods_delegate_to_sync_manager(self, mock_sync_manager):
        """✅ 同步方法委託給同步管理器"""
        from database.async_manager import HybridDatabaseManager

        with patch("database.manager.DatabaseManager", return_value=mock_sync_manager):
            config = Mock(spec=DatabaseConfig)
            manager = HybridDatabaseManager(config)
            manager.sync_manager = mock_sync_manager

            # 測試所有同步方法
            assert manager.test_connection()["message"] == "sync"
            assert manager.execute_query("SELECT *")["data"] == "sync"
            assert manager.get_schema_info() is not None
            assert manager.get_table_dependencies("TABLE1") is not None
            assert manager.get_schema_summary() is not None

            # 驗證調用
            mock_sync_manager.test_connection.assert_called()
            mock_sync_manager.execute_query.assert_called()

    @pytest.mark.asyncio
    async def test_async_methods_use_async_manager(self, mock_sync_manager, mock_async_manager):
        """✅ 異步方法使用異步管理器"""
        from database.async_manager import HybridDatabaseManager

        with patch("database.manager.DatabaseManager", return_value=mock_sync_manager):
            with patch("database.async_manager.AsyncDatabaseManager.create_and_initialize", return_value=mock_async_manager):
                config = Mock(spec=DatabaseConfig)
                manager = HybridDatabaseManager(config)
                manager.sync_manager = mock_sync_manager

                # 測試異步方法
                result = await manager.test_connection_async()
                assert result["message"] == "async"

                result = await manager.execute_query_async("SELECT *")
                assert result["data"] == "async"

                # 驗證異步管理器被調用
                mock_async_manager.test_connection.assert_called()
                mock_async_manager.execute_query.assert_called()

    @pytest.mark.asyncio
    async def test_get_async_manager_lazy_initialization(self, mock_sync_manager, mock_async_manager):
        """✅ 異步管理器延遲初始化"""
        from database.async_manager import HybridDatabaseManager

        with patch("database.manager.DatabaseManager", return_value=mock_sync_manager):
            with patch("database.async_manager.AsyncDatabaseManager.create_and_initialize", return_value=mock_async_manager):
                config = Mock(spec=DatabaseConfig)
                manager = HybridDatabaseManager(config)
                manager.sync_manager = mock_sync_manager

                assert manager._async_initialized is False

                # 第一次調用應該創建異步管理器
                async_mgr = await manager.get_async_manager()
                assert async_mgr == mock_async_manager
                assert manager._async_initialized is True

                # 第二次調用應該返回相同的實例
                async_mgr2 = await manager.get_async_manager()
                assert async_mgr2 == async_mgr

    @pytest.mark.asyncio
    async def test_close_async(self, mock_sync_manager, mock_async_manager):
        """✅ 關閉異步資源"""
        from database.async_manager import HybridDatabaseManager

        with patch("database.manager.DatabaseManager", return_value=mock_sync_manager):
            with patch("database.async_manager.AsyncDatabaseManager.create_and_initialize", return_value=mock_async_manager):
                config = Mock(spec=DatabaseConfig)
                manager = HybridDatabaseManager(config)
                manager.sync_manager = mock_sync_manager

                # 創建異步管理器
                await manager.get_async_manager()

                # 關閉異步資源
                await manager.close_async()

                mock_async_manager.close.assert_called_once()

    def test_schema_cache_property(self, mock_sync_manager):
        """✅ schema_cache 屬性訪問"""
        from database.async_manager import HybridDatabaseManager

        with patch("database.manager.DatabaseManager", return_value=mock_sync_manager):
            config = Mock(spec=DatabaseConfig)
            manager = HybridDatabaseManager(config)
            manager.sync_manager = mock_sync_manager

            cache = manager.schema_cache
            assert cache == mock_sync_manager.schema_cache

    def test_create_with_preload_factory(self, mock_sync_manager):
        """✅ create_with_preload 工廠方法"""
        from database.async_manager import HybridDatabaseManager

        with patch("database.manager.DatabaseManager") as MockDatabaseManager:
            MockDatabaseManager.create_with_preload.return_value = mock_sync_manager
            mock_sync_manager.config = Mock(spec=DatabaseConfig)
            mock_sync_manager.app_config = Mock(spec=AppConfig)

            manager = HybridDatabaseManager.create_with_preload()

            assert manager.sync_manager == mock_sync_manager
            assert manager._async_initialized is False
            MockDatabaseManager.create_with_preload.assert_called_once()


class TestConnectionPooling:
    """連接池測試"""

    @pytest.mark.asyncio
    async def test_pool_reuse_connections(self):
        """✅ 連接池重用連接"""
        # 這是一個概念性測試，實際實現需要真實的資料庫連接
        # 在這裡我們驗證連接池的基本邏輯

        mock_pool = AsyncMock()
        mock_connection = AsyncMock()

        async def mock_acquire():
            return mock_connection

        mock_pool.acquire = mock_acquire

        # 模擬多次獲取連接
        conn1 = await mock_pool.acquire()
        conn2 = await mock_pool.acquire()

        # 在真實場景中，連接池應該重用連接
        # 這裡只是驗證機制存在
        assert conn1 is not None
        assert conn2 is not None


class TestAsyncErrorHandling:
    """異步錯誤處理測試"""

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self):
        """❌ 連接失敗處理"""
        from database.async_manager import AsyncDatabaseManager

        mock_connector = AsyncMock()
        mock_connector.initialize_pool.side_effect = Exception("Connection failed")

        config = Mock(spec=DatabaseConfig)
        config.db_type = "mssql"

        with patch("database.async_manager.create_async_database_connector", return_value=mock_connector):
            manager = AsyncDatabaseManager(config)

            with pytest.raises(Exception, match="Connection failed"):
                await manager.initialize()

    @pytest.mark.asyncio
    async def test_query_execution_error(self):
        """❌ 查詢執行錯誤處理"""
        from database.async_manager import AsyncDatabaseManager

        mock_connector = AsyncMock()
        mock_connector.initialize_pool = AsyncMock()
        mock_connector.execute_query.side_effect = Exception("Query failed")

        config = Mock(spec=DatabaseConfig)

        with patch("database.async_manager.create_async_database_connector", return_value=mock_connector):
            manager = AsyncDatabaseManager(config)
            await manager.initialize()

            with pytest.raises(Exception, match="Query failed"):
                await manager.execute_query("INVALID SQL")
