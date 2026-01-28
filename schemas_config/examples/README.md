# Schema 配置範例

本目錄包含範例配置檔案，幫助您為自己的資料庫設定 `schemas_config/`。

## 檔案

- **`sample_table.json`** - 完整的表格配置範例，展示所有可用欄位與格式。建立您自己的 `tables/*.json` 檔案時，可以此作為參考。

## 使用方式

1. 將 `sample_table.json` 複製到 `../tables/YOUR_TABLE.json`
2. 將表格名稱、欄位、關聯與業務邏輯替換為您自己的內容
3. 在 `../tables_list.json` 的 `tables` 鍵下註冊該表格
4. 重新啟動 MCP 伺服器或 HTTP API 以載入新配置

## 最小化配置

您不需要所有欄位。最小化的表格配置只需要：

```json
{
  "table_name": "YOUR_TABLE",
  "display_name": "您的表格",
  "key_columns": {
    "ID": {
      "semantic_type": "primary_identifier",
      "description": "主鍵"
    }
  }
}
```

系統會自動為未明確定義的欄位套用 `global_patterns.json` 規則。
