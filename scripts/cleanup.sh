#!/bin/bash

# MCP Database 專案清理腳本
# 用於清理開發過程中產生的臨時檔案和快取

set -e

echo "🧹 開始清理 MCP Database 專案..."

# 設定專案根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "📂 專案目錄: $PROJECT_ROOT"

# 清理 Python 快取檔案
echo "🐍 清理 Python 快取檔案..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*.pyd" -delete 2>/dev/null || true

# 清理編譯檔案
echo "🔧 清理編譯檔案..."
find . -name "*.so" -delete 2>/dev/null || true
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true

# 清理臨時檔案
echo "📄 清理臨時檔案..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true

# 清理編輯器備份檔案
echo "✏️ 清理編輯器備份檔案..."
find . -name ".*.swp" -delete 2>/dev/null || true
find . -name ".*.swo" -delete 2>/dev/null || true
find . -name "*.orig" -delete 2>/dev/null || true

# 清理遺留的開發檔案
echo "🗂️ 清理遺留的開發檔案..."
find . -name "*_old.py" -delete 2>/dev/null || true
find . -name "*_legacy.py" -delete 2>/dev/null || true
find . -name "*_backup.py" -delete 2>/dev/null || true
find . -name "*_test.py" -not -path "./tests/*" -delete 2>/dev/null || true

# 清理版本號檔案 (除了合法的版本檔案)
echo "📌 清理版本檔案..."
find . -name "*_v[0-9]*.py" -delete 2>/dev/null || true

# 清理快取目錄
echo "💾 清理快取目錄..."
[ -d ".pytest_cache" ] && rm -rf .pytest_cache
[ -d ".mypy_cache" ] && rm -rf .mypy_cache
[ -d ".coverage" ] && rm -rf .coverage

# 清理 IDE 檔案
echo "💻 清理 IDE 檔案..."
[ -d ".vscode" ] && rm -rf .vscode
[ -d ".idea" ] && rm -rf .idea
find . -name "*.code-workspace" -delete 2>/dev/null || true

# 清理 Jupyter 檔案
echo "📓 清理 Jupyter 檔案..."
find . -name ".ipynb_checkpoints" -type d -exec rm -rf {} + 2>/dev/null || true

# 清理系統檔案
echo "🖥️ 清理系統檔案..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true

# 清理日誌檔案
echo "📝 清理日誌檔案..."
find . -name "*.log" -not -path "./logs/*" -delete 2>/dev/null || true

# 清理匯出目錄
echo "📤 清理匯出目錄..."
[ -d "schema_export" ] && rm -rf schema_export
[ -d "exports" ] && rm -rf exports

# 清理 Docker volumes (謹慎)
if [ "$1" = "--deep" ]; then
    echo "🐳 深度清理 Docker volumes..."
    [ -d "sqlserver_data" ] && rm -rf sqlserver_data
    echo "⚠️ 注意：已清理 Docker volumes，下次啟動 Docker 時會重新創建"
fi

# 顯示清理結果
echo ""
echo "✅ 清理完成！"
echo ""
echo "📊 專案狀態："
echo "   Python 檔案: $(find src -name "*.py" | wc -l) 個"
echo "   文檔檔案: $(find docs -name "*.md" 2>/dev/null | wc -l) 個"
echo "   配置檔案: $(find . -maxdepth 1 -name "*.json" -o -name "*.toml" -o -name "*.yaml" -o -name "*.yml" | wc -l) 個"

# 檢查是否有遺留的舊檔案
OLD_FILES=$(find . -name "*_old*" -o -name "*_legacy*" -o -name "*_backup*" -o -name "*_v[0-9]*" 2>/dev/null | wc -l)
if [ "$OLD_FILES" -gt 0 ]; then
    echo "⚠️ 警告：發現 $OLD_FILES 個可能的遺留檔案，請手動檢查"
    find . -name "*_old*" -o -name "*_legacy*" -o -name "*_backup*" -o -name "*_v[0-9]*" 2>/dev/null
fi

echo ""
echo "💡 使用說明："
echo "   $ ./scripts/cleanup.sh          # 一般清理"
echo "   $ ./scripts/cleanup.sh --deep   # 深度清理 (包含 Docker volumes)"
echo ""