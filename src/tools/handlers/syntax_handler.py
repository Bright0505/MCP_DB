"""SQL syntax guide handler."""

import logging
from typing import Any, Dict, List
from mcp.types import CallToolRequest

from tools.base import ToolHandler
from tools.definitions import make_tool_name, TOOL_SYNTAX_GUIDE

logger = logging.getLogger(__name__)


class SyntaxHandler(ToolHandler):
    """Handler for SQL syntax guide."""

    @property
    def tool_names(self) -> List[str]:
        return [make_tool_name(TOOL_SYNTAX_GUIDE)]

    async def handle(self, request: CallToolRequest, db_manager: Any) -> Dict[str, Any]:
        """
        Provide SQL Server syntax reference.

        Args:
            request: MCP tool call request
            db_manager: Database manager instance

        Returns:
            SQL syntax guide
        """
        # Get database type from config
        db_type = db_manager.config.db_type
        
        if db_type == "mssql":
            guide = self._get_mssql_syntax_guide()
        elif db_type == "postgresql":
            guide = self._get_postgresql_syntax_guide()
        else:
            guide = "📚 SQL Syntax Guide\n\nDatabase type not recognized."
        
        return self._success_response(guide)

    def _get_mssql_syntax_guide(self) -> str:
        """Get SQL Server (T-SQL) syntax guide."""
        return """📚 SQL Server (T-SQL) Syntax Guide

🔍 **Basic Query Structure**:
```sql
SELECT TOP 10 column1, column2
FROM table_name
WHERE condition
ORDER BY column1 DESC
```

⏰ **Date/Time Functions**:
- Current date/time: `GETDATE()`
- Date only: `CAST(GETDATE() AS DATE)`
- Add days: `DATEADD(DAY, 7, GETDATE())`
- Difference: `DATEDIFF(DAY, start_date, end_date)`
- Extract parts: `YEAR(date)`, `MONTH(date)`, `DAY(date)`

📊 **Common Patterns**:

**Today's records**:
```sql
WHERE CAST(date_column AS DATE) = CAST(GETDATE() AS DATE)
```

**This month**:
```sql
WHERE YEAR(date_column) = YEAR(GETDATE())
  AND MONTH(date_column) = MONTH(GETDATE())
```

**Last 7 days**:
```sql
WHERE date_column >= DATEADD(DAY, -7, GETDATE())
```

**Top N records**:
```sql
SELECT TOP 100 * FROM table_name ORDER BY id DESC
```

🔗 **Joins**:
```sql
SELECT a.*, b.column
FROM table_a a
INNER JOIN table_b b ON a.id = b.a_id
```

📋 **Aggregation**:
```sql
SELECT 
    category,
    COUNT(*) as count,
    SUM(amount) as total,
    AVG(amount) as average
FROM table_name
GROUP BY category
HAVING COUNT(*) > 10
```

💡 **Tips**:
- Use `TOP N` instead of `LIMIT`
- Use `GETDATE()` instead of `NOW()` or `CURDATE()`
- String concatenation: `column1 + ' ' + column2`
- Case-insensitive comparison is default
- Use `CAST()` or `CONVERT()` for type conversion
"""

    def _get_postgresql_syntax_guide(self) -> str:
        """Get PostgreSQL syntax guide."""
        return """📚 PostgreSQL Syntax Guide

🔍 **Basic Query Structure**:
```sql
SELECT column1, column2
FROM table_name
WHERE condition
ORDER BY column1 DESC
LIMIT 10
```

⏰ **Date/Time Functions**:
- Current date/time: `NOW()` or `CURRENT_TIMESTAMP`
- Date only: `CURRENT_DATE`
- Add interval: `NOW() + INTERVAL '7 days'`
- Difference: `date2 - date1`
- Extract parts: `EXTRACT(YEAR FROM date)`

📊 **Common Patterns**:

**Today's records**:
```sql
WHERE DATE(timestamp_column) = CURRENT_DATE
```

**This month**:
```sql
WHERE DATE_TRUNC('month', timestamp_column) = DATE_TRUNC('month', CURRENT_DATE)
```

**Last 7 days**:
```sql
WHERE timestamp_column >= NOW() - INTERVAL '7 days'
```

**Limit records**:
```sql
SELECT * FROM table_name ORDER BY id DESC LIMIT 100
```

💡 **Tips**:
- Use `LIMIT N` for row limits
- Use `NOW()` for current timestamp
- String concatenation: `column1 || ' ' || column2`
- Case-sensitive by default (use `ILIKE` for case-insensitive)
- Use `::type` for type casting: `column::integer`
"""
