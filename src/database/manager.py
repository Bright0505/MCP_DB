"""Database connection and query execution."""

import logging
import threading
from typing import Any, Dict, List, Optional, Union
from core.config import DatabaseConfig, AppConfig
from database.connectors import create_database_connector, DatabaseConnector
from database.schema.introspector import create_schema_inspector
from database.schema.cache import SchemaCache, SchemaPreloader, CachedSchemaIntrospector

logger = logging.getLogger(__name__)

# Global schema cache instance (singleton pattern)
_global_schema_cache: Optional[SchemaCache] = None
_cache_lock = threading.RLock()


def get_or_create_global_cache(cache_ttl_minutes: int = 60) -> SchemaCache:
    """Get or create the global schema cache instance."""
    global _global_schema_cache
    with _cache_lock:
        if _global_schema_cache is None:
            _global_schema_cache = SchemaCache(cache_ttl_minutes=cache_ttl_minutes)
            logger.info(f"[CACHE-SINGLETON] Created global cache, cache_id={id(_global_schema_cache)}, ttl={cache_ttl_minutes}min")
        return _global_schema_cache


class DatabaseManager:
    """Manages database connections and operations for multiple database types."""

    def __init__(self, config: DatabaseConfig, app_config: Optional[AppConfig] = None):
        self.config = config
        self.db_connector = create_database_connector(config)

        # Setup schema caching if enabled
        self.app_config = app_config or AppConfig.from_env()
        self.schema_cache = None
        self.schema_preloader = None
        self.schema_introspector = None

        self._initialize_schema_system()

    def _initialize_schema_system(self):
        """Initialize schema introspection with optional caching."""
        base_introspector = create_schema_inspector(self.get_connection, self.config)

        if self.app_config.schema_config.enable_cache:
            # Use global singleton cache to ensure sharing across instances
            self.schema_cache = get_or_create_global_cache(
                cache_ttl_minutes=self.app_config.schema_config.cache_ttl_minutes
            )
            logger.info(f"[MANAGER] Using global cache, cache_id={id(self.schema_cache)}, ttl={self.app_config.schema_config.cache_ttl_minutes}min")

            # Use cached introspector
            self.schema_introspector = CachedSchemaIntrospector(
                base_introspector,
                self.schema_cache,
                strict_mode=self.app_config.schema_config.strict_mode
            )
            logger.info(f"[MANAGER] Introspector using cache_id={id(self.schema_cache)}, strict_mode={self.app_config.schema_config.strict_mode}")

            # Setup preloader
            self.schema_preloader = SchemaPreloader(
                base_introspector, self.schema_cache
            )
            logger.info(f"[MANAGER] Preloader using cache_id={id(self.schema_cache)}")

            # Load and preload schemas if configured
            if self.app_config.schema_config.preload_on_startup:
                self._try_schema_preload()
        else:
            # Use base introspector without caching
            self.schema_introspector = base_introspector

    def _try_schema_preload(self):
        """Try to preload schemas on startup."""
        try:
            config_path = self.app_config.schema_config.get_config_path()
            if config_path and self.schema_preloader:
                logger.info(f"Loading schema configuration from: {config_path}")
                success = self.schema_preloader.load_config_and_preload(
                    str(config_path),
                    max_concurrent=self.app_config.schema_config.max_concurrent_queries
                )
                if success:
                    logger.info("✅ Schema preload completed successfully")
                else:
                    logger.error("❌ Failed to load schema configuration")
            else:
                logger.info("No schema configuration found, skipping preload")

        except Exception as e:
            logger.error(f"Schema preload failed: {e}")

    @classmethod
    def create_with_preload(cls, config: DatabaseConfig = None, app_config: AppConfig = None):
        """Factory method to create DatabaseManager with preload enabled."""
        if not app_config:
            app_config = AppConfig.from_env()
            # Force preload on startup
            app_config.schema_config.preload_on_startup = True

        if not config:
            config = app_config.database

        return cls(config, app_config)

    def get_connection(self):
        """Context manager for database connections with enhanced error handling."""
        return self.db_connector.get_connection()

    def test_connection(self, include_sensitive_info: Optional[bool] = None) -> Dict[str, Any]:
        """Test database connectivity with detailed error information.

        Args:
            include_sensitive_info: If True, include server details.
                                   If None, uses app_config.expose_sensitive_info.
        """
        result = self.db_connector.test_connection()

        # Check if we should expose sensitive info
        expose = include_sensitive_info
        if expose is None:
            expose = self.app_config.expose_sensitive_info

        # Remove sensitive information if not allowed
        if not expose and result.get('success'):
            if 'server_info' in result:
                # Keep only essential info, remove sensitive details
                server_info = result['server_info']
                sanitized_info = {
                    'database': server_info.get('current_database', server_info.get('database')),
                    'connected': True
                }
                result['server_info'] = sanitized_info

        return result

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute a SQL query and return results."""
        return self.db_connector.execute_query(query, params)

    def execute_command(self, command: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute a SQL command (INSERT/UPDATE/DELETE) and return result."""
        return self.db_connector.execute_command(command, params)

    def get_schema_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive database schema information."""
        return self.schema_introspector.get_schema_info(table_name)

    def get_table_dependencies(self, table_name: str) -> Dict[str, Any]:
        """Get table dependencies (foreign keys, referenced by)."""
        return self.schema_introspector.get_table_dependencies(table_name)

    def get_schema_summary(self) -> Dict[str, Any]:
        """Get a high-level summary of the database schema."""
        return self.schema_introspector.get_schema_summary()

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get comprehensive database information.

        Called by posdb_schema_summary tool handler.
        Wraps get_schema_summary() with enhanced formatting and server info.

        Returns:
            Dict with database info including:
            - success: bool
            - database_type: str (mssql/postgresql)
            - database_name: str
            - server_name: str
            - summary: Dict with total_tables, total_views, etc.
        """
        try:
            # 1. Get schema summary
            summary = self.schema_introspector.get_schema_summary()

            if not summary.get("success"):
                return summary

            # 2. Get connection info
            conn_info = self.test_connection(include_sensitive_info=False)

            # 3. Build result based on database type
            db_type = summary.get("database_type", "unknown")

            result = {
                "success": True,
                "database_type": db_type,
                "database_name": conn_info.get("server_info", {}).get("database", "N/A"),
                "server_name": conn_info.get("server_info", {}).get("server", "N/A"),
                "summary": {}
            }

            # 4. Format summary
            if db_type == "mssql":
                result["summary"] = {
                    "total_tables": summary.get("tables", 0),
                    "total_views": summary.get("views", 0),
                    "total_procedures": summary.get("procedures", 0),
                    "total_functions": summary.get("functions", 0)
                }
            else:  # postgresql
                pg_summary = summary.get("summary", {})
                result["summary"] = {
                    "total_tables": pg_summary.get("Tables", 0),
                    "total_views": pg_summary.get("Views", 0),
                    "total_procedures": 0,
                    "total_functions": 0
                }

            return result

        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get database info: {str(e)}"
            }

    def invalidate_schema_cache(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Invalidate schema cache entries."""
        try:
            if hasattr(self.schema_introspector, 'invalidate_cache'):
                self.schema_introspector.invalidate_cache(table_name)
                return {
                    "success": True,
                    "message": f"Cache invalidated for {'all tables' if not table_name else table_name}"
                }
            else:
                return {
                    "success": False,
                    "message": "Schema caching not enabled"
                }
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to invalidate cache: {str(e)}"
            }

    def clear_all_cache(self) -> Dict[str, Any]:
        """
        Clear all schema cache entries.

        Called by posdb_cache_invalidate when table_name is None.

        Returns:
            Dict with success, message, and cleared_count
        """
        try:
            # Check if caching is enabled
            if not hasattr(self.schema_introspector, 'invalidate_cache'):
                return {
                    "success": False,
                    "message": "Schema caching not enabled"
                }

            # Get cache size before clearing
            cleared_count = 0
            if self.schema_cache:
                with self.schema_cache._lock:
                    cleared_count = len(self.schema_cache.cache)

            # Clear cache
            self.schema_introspector.invalidate_cache(table_name=None)

            return {
                "success": True,
                "message": "All cache cleared successfully",
                "cleared_count": cleared_count
            }

        except Exception as e:
            logger.error(f"Failed to clear all cache: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to clear cache: {str(e)}"
            }

    def reload_schema_config(self) -> Dict[str, Any]:
        """Reload schema configuration from file."""
        try:
            if not self.schema_preloader:
                return {
                    "success": False,
                    "message": "Schema preloader not available (caching disabled)"
                }

            config_path = self.app_config.schema_config.get_config_path()
            if not config_path:
                return {
                    "success": False,
                    "message": "No schema configuration file path specified"
                }

            success = self.schema_preloader.load_config_and_preload(
                str(config_path),
                max_concurrent=self.app_config.schema_config.max_concurrent_queries
            )

            if success:
                return {
                    "success": True,
                    "message": f"Schema configuration reloaded from {config_path}"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to load schema configuration from {config_path}"
                }

        except Exception as e:
            logger.error(f"Failed to reload schema config: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to reload schema config: {str(e)}"
            }

    def get_schema_cache_stats(self) -> Dict[str, Any]:
        """Get schema cache statistics."""
        try:
            if not self.schema_cache:
                return {
                    "success": True,
                    "cache_enabled": False,
                    "message": "Schema caching not enabled"
                }

            return {
                "success": True,
                "cache_enabled": True,
                "cache_size": len(self.schema_cache.cache),
                "cache_ttl_minutes": self.app_config.schema_config.cache_ttl_minutes,
                "preload_enabled": self.app_config.schema_config.preload_on_startup,
                "cached_keys": list(self.schema_cache.cache.keys())
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get cache stats: {str(e)}"
            }

    def get_cache_debug_info(self) -> Dict[str, Any]:
        """Get detailed cache debugging information."""
        try:
            if not self.schema_cache:
                return {"success": True, "cache_enabled": False, "message": "Schema caching not enabled"}

            from datetime import datetime
            with self.schema_cache._lock:
                cache_keys = list(self.schema_cache.cache.keys())
                cache_details = {}

                for key in cache_keys:
                    cache_details[key] = {
                        "has_value": key in self.schema_cache.cache,
                        "is_valid": self.schema_cache._is_valid(key),
                        "last_updated": self.schema_cache.last_updated.get(key).isoformat()
                            if key in self.schema_cache.last_updated else None,
                        "age_seconds": (datetime.now() - self.schema_cache.last_updated[key]).total_seconds()
                            if key in self.schema_cache.last_updated else None
                    }

                return {
                    "success": True,
                    "cache_enabled": True,
                    "cache_id": id(self.schema_cache),
                    "total_keys": len(cache_keys),
                    "cache_keys": cache_keys,
                    "cache_details": cache_details,
                    "ttl_minutes": self.app_config.schema_config.cache_ttl_minutes,
                    "strict_mode": self.app_config.schema_config.strict_mode
                }

        except Exception as e:
            logger.error(f"Failed to get cache debug info: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get cache debug info: {str(e)}"
            }

    def get_static_schema_info(self) -> Dict[str, Any]:
        """Get information about static schema files."""
        try:
            from database.schema.static_loader import get_schema_manager
            manager = get_schema_manager()
            summary = manager.get_summary()

            return {
                "success": True,
                "static_schema_files": summary.get('total_tables', 0),
                "schema_directory": "schemas_config/",
                "total_tables": summary.get('total_tables', 0),
                "total_columns": summary.get('total_columns', 0),
                "json_configs": summary.get('config_status', {}).get('json_configs_loaded', 0),
                "message": f"Found {summary.get('total_tables', 0)} tables via JSON config system"
            }

        except Exception as e:
            logger.error(f"Failed to get static schema info: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get static schema info: {str(e)}"
            }

    def export_table_schema(
        self,
        table_name: str,
        output_dir: str = "schema_export",
        include_business_logic: bool = True
    ) -> Dict[str, Any]:
        """
        Export table schema to a JSON file.

        Called by posdb_export_schema tool handler.

        Args:
            table_name: Name of table to export
            output_dir: Output directory (default: "schema_export")
            include_business_logic: Include AI context (default: True)

        Returns:
            Dict with success, file_path, column_count, file_size_bytes
        """
        try:
            import json
            from pathlib import Path
            from datetime import datetime

            # 1. Get table schema
            schema_result = self.get_schema_info(table_name)

            if not schema_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to get schema for table {table_name}",
                    "error": schema_result.get("error", "Unknown error")
                }

            # 2. Build export data
            export_data = {
                "table_name": table_name,
                "exported_at": datetime.now().isoformat(),
                "database_type": schema_result.get("database_type", "unknown"),
                "total_columns": schema_result.get("total_count", 0),
                "columns": schema_result.get("results", [])
            }

            # 3. Add enhanced metadata
            if include_business_logic:
                for key in ["business_logic", "ai_context", "relationships",
                           "display_name", "category", "business_importance"]:
                    if key in schema_result:
                        export_data[key] = schema_result[key]

            # 4. Ensure output directory exists
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 5. Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{table_name}_schema_{timestamp}.json"
            file_path = output_path / filename

            # 6. Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Exported schema for {table_name} to {file_path}")

            return {
                "success": True,
                "message": "Schema exported successfully",
                "file_path": str(file_path.absolute()),
                "table_name": table_name,
                "column_count": export_data["total_columns"],
                "file_size_bytes": file_path.stat().st_size
            }

        except Exception as e:
            logger.error(f"Failed to export schema for {table_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Export failed: {str(e)}"
            }