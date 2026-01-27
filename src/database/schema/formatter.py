"""Schema formatter for generating standard schema documentation."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class SchemaFormatter:
    """Formats database schema information into standard documentation."""

    def __init__(self):
        self.column_width_mapping = {
            'COLUMN_NAME': 15,
            'DATA_TYPE': 15,
            'DESCRIPTION': 20,
            'REMARKS': 20
        }

    def format_table_schema(self,
                          table_name: str,
                          columns: List[Dict[str, Any]],
                          table_comment: Optional[str] = None,
                          business_descriptions: Optional[Dict[str, str]] = None) -> str:
        """
        Format table schema into standard documentation.

        Args:
            table_name: Name of the table
            columns: List of column information dictionaries
            table_comment: Optional table description
            business_descriptions: Optional mapping of column names to business descriptions

        Returns:
            Formatted schema documentation string
        """
        business_descriptions = business_descriptions or {}

        # Extract Chinese table name if available in comment
        display_name = self._extract_display_name(table_name, table_comment)

        lines = []
        lines.append(f"分頁名稱: {display_name}")
        lines.append("=" * 50)
        lines.append("")

        # Header
        lines.append(f"{'資料欄位':>15} {'資料類型':>15} {'說明':>20} {'備註':>20}")

        # Column information
        for col in columns:
            column_name = col.get('COLUMN_NAME', '')
            data_type = self._format_data_type(col)
            description = self._get_column_description(column_name, col, business_descriptions)
            remarks = self._get_column_remarks(col)

            lines.append(f"{column_name:>15} {data_type:>15} {description:>20} {remarks:>20}")

        return '\n'.join(lines)

    def _extract_display_name(self, table_name: str, table_comment: Optional[str]) -> str:
        """Extract display name from table name and comment."""
        if table_comment and any('\u4e00' <= char <= '\u9fff' for char in table_comment):
            # Has Chinese characters
            return f"{table_name} {table_comment}"
        return table_name

    def _format_data_type(self, column: Dict[str, Any]) -> str:
        """Format data type information."""
        data_type = column.get('DATA_TYPE', '').lower()

        # Handle length/precision
        if data_type in ['nvarchar', 'varchar', 'char', 'nchar']:
            max_length = column.get('CHARACTER_MAXIMUM_LENGTH')
            if max_length:
                return f"{data_type}({max_length})"

        elif data_type in ['decimal', 'numeric']:
            precision = column.get('NUMERIC_PRECISION')
            scale = column.get('NUMERIC_SCALE')
            if precision is not None and scale is not None:
                return f"{data_type}({precision}, {scale})"
            elif precision is not None:
                return f"{data_type}({precision})"

        elif data_type in ['float', 'real']:
            precision = column.get('NUMERIC_PRECISION')
            if precision:
                return f"{data_type}({precision})"

        return data_type

    def _get_column_description(self, column_name: str,
                              column: Dict[str, Any],
                              business_descriptions: Dict[str, str]) -> str:
        """Get column description with business context."""
        # Priority: business_descriptions > column comment > generate from name
        if column_name in business_descriptions:
            return business_descriptions[column_name]

        # Try to get from column comment/description
        description = column.get('COLUMN_COMMENT') or column.get('DESCRIPTION', '')
        if description:
            return description

        # Generate basic description from column name patterns
        return self._generate_description_from_name(column_name)

    def _generate_description_from_name(self, column_name: str) -> str:
        """Generate basic description from column name patterns."""
        name_lower = column_name.lower()

        # Common patterns
        if name_lower.endswith('_id'):
            return f"{column_name.replace('_ID', '').replace('_id', '')}編號"
        elif name_lower.endswith('_no') or name_lower.endswith('_sno'):
            return f"{column_name.replace('_NO', '').replace('_no', '').replace('_SNO', '').replace('_sno', '')}序號"
        elif name_lower.endswith('_name'):
            return f"{column_name.replace('_NAME', '').replace('_name', '')}名稱"
        elif name_lower.endswith('_date'):
            return f"{column_name.replace('_DATE', '').replace('_date', '')}日期"
        elif name_lower.endswith('_time'):
            return f"{column_name.replace('_TIME', '').replace('_time', '')}時間"
        elif name_lower in ['quantity', 'qty']:
            return "數量"
        elif name_lower in ['price', 'amount']:
            return "金額"
        elif name_lower in ['status']:
            return "狀態"
        elif name_lower.startswith('is') or name_lower.endswith('_flag'):
            return "旗標"
        elif name_lower.endswith('_update'):
            return "更新時間"
        elif name_lower.endswith('_create'):
            return "建立時間"
        else:
            return ""

    def _get_column_remarks(self, column: Dict[str, Any]) -> str:
        """Get column remarks including constraints and relationships."""
        remarks = []

        # Primary key
        if column.get('IS_PRIMARY_KEY') == 'YES':
            remarks.append("主鍵")

        # Foreign key
        if column.get('IS_FOREIGN_KEY') == 'YES':
            ref_table = column.get('REFERENCED_TABLE_NAME')
            ref_column = column.get('REFERENCED_COLUMN_NAME')
            if ref_table:
                remarks.append(f"對應{ref_table}.{ref_column}")

        # Nullable
        if column.get('IS_NULLABLE') == 'NO':
            remarks.append("必填")

        # Default value
        default_value = column.get('COLUMN_DEFAULT')
        if default_value and default_value not in ['NULL', 'null']:
            remarks.append(f"預設:{default_value}")

        return " ".join(remarks)

    def save_schema_to_file(self,
                           schema_content: str,
                           table_name: str,
                           output_dir: str = "schema_export") -> str:
        """
        Save schema content to a file.

        Args:
            schema_content: The formatted schema content
            table_name: Name of the table
            output_dir: Output directory for the file

        Returns:
            Path to the saved file
        """
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{table_name}_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(schema_content)
            f.write(f"\n\n# 生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            f.write(f"\n# 表格名稱: {table_name}")

        return filepath

    def format_table_list(self, tables: List[Dict[str, Any]]) -> str:
        """
        Format table list into standard documentation.

        Args:
            tables: List of table information dictionaries with TABLE_NAME, TABLE_TYPE, TABLE_COMMENT

        Returns:
            Formatted table list documentation string
        """
        lines = []
        lines.append("資料庫表格清單")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"{'表格名稱':>25} {'類型':>10} {'說明':>30}")
        lines.append("-" * 70)

        # Sort tables by type and name
        sorted_tables = sorted(tables, key=lambda x: (x.get('TABLE_TYPE', ''), x.get('TABLE_NAME', '')))

        current_type = None
        for table in sorted_tables:
            table_name = table.get('TABLE_NAME', '')
            table_type = table.get('TABLE_TYPE', '')
            table_comment = table.get('TABLE_COMMENT', '')

            # Group by table type
            if current_type != table_type:
                if current_type is not None:
                    lines.append("")  # Add blank line between types
                current_type = table_type
                lines.append(f"# {table_type}")
                lines.append("")

            # Format comment
            if table_comment:
                # Truncate long comments
                if len(table_comment) > 25:
                    display_comment = table_comment[:22] + "..."
                else:
                    display_comment = table_comment
            else:
                display_comment = "(無說明)"

            # Format table type for display
            type_display = "表格" if table_type == "BASE TABLE" else "檢視"

            lines.append(f"{table_name:>25} {type_display:>10} {display_comment:>30}")

            # If comment was truncated, add full comment on next line
            if table_comment and len(table_comment) > 25:
                lines.append(f"{'':>37}完整說明: {table_comment}")

        lines.append("")
        lines.append(f"總計: {len(tables)} 個資料庫物件")

        return '\n'.join(lines)

    def save_table_list_to_file(self,
                               table_list_content: str,
                               output_dir: str = "schema_export") -> str:
        """
        Save table list content to table_list.txt file.

        Args:
            table_list_content: The formatted table list content
            output_dir: Output directory for the file

        Returns:
            Path to the saved file
        """
        os.makedirs(output_dir, exist_ok=True)

        filename = "table_list.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(table_list_content)
            f.write(f"\n\n# 生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            f.write(f"\n# 資料庫類型: SQL Server / PostgreSQL")

        return filepath


class BusinessLogicEnhancer:
    """Enhances schema with business logic and descriptions using dynamic patterns."""

    def __init__(self):
        # Load from static schemas if available
        self.static_mappings = self._load_static_mappings()

        # Generic pattern-based mappings (fallback)
        self.pattern_mappings = self._get_generic_patterns()

    def _load_static_mappings(self) -> Dict[str, str]:
        """Load business mappings from schema manager."""
        try:
            from database.schema.static_loader import get_schema_manager

            mappings = {}
            manager = get_schema_manager()

            # Get all tables and extract column descriptions
            tables = manager.get_all_tables()
            for table in tables:
                table_name = table['TABLE_NAME']
                schema = manager.get_table_schema(table_name)
                if schema and schema.get('columns'):
                    for column in schema['columns']:
                        col_name = column.get('COLUMN_NAME', '').upper()
                        # Check for enhanced descriptions from JSON configs
                        description = (
                            column.get('enhanced_description') or
                            column.get('DESCRIPTION') or
                            column.get('COLUMN_COMMENT')
                        )
                        if description:
                            mappings[col_name] = description

            return mappings
        except (ImportError, AttributeError, KeyError) as e:
            logger.debug(f"無法載入業務映射: {e}")
            return {}

    def _get_generic_patterns(self) -> Dict[str, str]:
        """Get generic column name patterns for business logic mapping."""
        return {
            # Generic ID patterns
            '_ID': '編號',
            '_NO': '序號',
            '_CODE': '代碼',

            # Generic name patterns
            '_NAME': '名稱',
            'NAME': '名稱',
            'TITLE': '標題',

            # Generic date/time patterns
            '_DATE': '日期',
            '_TIME': '時間',
            'DATE': '日期',
            'TIME': '時間',
            'CREATED': '建立時間',
            'UPDATED': '更新時間',
            'MODIFIED': '修改時間',

            # Generic amount/quantity patterns
            'AMOUNT': '金額',
            'PRICE': '價格',
            'COST': '成本',
            'QTY': '數量',
            'QUANTITY': '數量',
            'COUNT': '計數',

            # Generic status patterns
            'STATUS': '狀態',
            'ACTIVE': '啓用狀態',
            'ENABLED': '啓用',
            'FLAG': '旗標',

            # Generic description patterns
            'DESCRIPTION': '描述',
            'DESC': '說明',
            'REMARKS': '備註',
            'NOTES': '註記',
            'COMMENT': '註解'
        }

    def enhance_column_descriptions(self, columns: List[Dict[str, Any]]) -> Dict[str, str]:
        """Enhance column descriptions with business logic using dynamic mapping."""
        enhanced = {}

        for col in columns:
            column_name = col.get('COLUMN_NAME', '').upper()

            # Priority 1: Static schema mappings (from database.schema.static_loader)
            if column_name in self.static_mappings:
                enhanced[column_name] = self.static_mappings[column_name]
                continue

            # Priority 2: Pattern-based mappings
            description = self._match_pattern(column_name)
            if description:
                enhanced[column_name] = description

        return enhanced

    def _match_pattern(self, column_name: str) -> Optional[str]:
        """Match column name against generic patterns."""
        column_upper = column_name.upper()

        # Exact match first
        if column_upper in self.pattern_mappings:
            return self.pattern_mappings[column_upper]

        # Pattern matching (suffix/contains)
        for pattern, description in self.pattern_mappings.items():
            if pattern.startswith('_') and column_upper.endswith(pattern):
                # Suffix pattern like '_ID', '_NAME'
                base_name = column_upper[:-len(pattern)]
                if base_name:
                    return f"{base_name.replace('_', '')}{description}"
            elif not pattern.startswith('_') and pattern in column_upper:
                # Contains pattern
                return description

        return None