# 扩展快速开始

本文档给新扩展建立最小调用闭环。示例使用 PowerShell 和 `curl.exe`，其他语言按同样请求结构实现即可。

## 1. 准备配置

扩展至少需要保存两个配置：

```text
MAKER_STASH_API_URL=http://127.0.0.1:8000
MAKER_STASH_TOKEN=<your-token>
```

Token 通过主干脚本创建，明文只显示一次：

```powershell
cd backend
& ..\.venv\Scripts\python.exe -m app.scripts.create_token --name scanner-extension
```

## 2. 检查主干能力

扩展启动时先读取 capabilities：

```powershell
curl.exe -H "Authorization: Bearer $env:MAKER_STASH_TOKEN" `
  "$env:MAKER_STASH_API_URL/api/system/capabilities"
```

扩展至少检查：

- `api_version` 是否在支持范围内。
- 需要的 `features` 是否为 `true`。
- 上传类扩展是否遵守 `limits.max_upload_bytes`。
- 高风险写入是否遵守 `extension_contract.workflow_required_for_bulk_or_agent_writes`。

## 3. 查询物品

```powershell
curl.exe -H "Authorization: Bearer $env:MAKER_STASH_TOKEN" `
  "$env:MAKER_STASH_API_URL/api/items?q=PLA&page=1&page_size=20"
```

只读查询可以直接调用基础 API。扩展应解析统一 envelope 中的 `success` 和 `data`。

## 4. 单步写入

单步低风险写入可以直接调用基础 API，但必须携带幂等键和来源字段：

```powershell
$body = @{
  amount = 1
  unit = "kg"
  note = "扩展入库"
  source = "extension"
  module = "scanner-extension"
  operator = "admin"
  request_id = "scanner-extension-add-20260528-000001"
} | ConvertTo-Json

curl.exe -X POST `
  -H "Authorization: Bearer $env:MAKER_STASH_TOKEN" `
  -H "Content-Type: application/json" `
  -d $body `
  "$env:MAKER_STASH_API_URL/api/items/FIL-000001/add"
```

网络失败后重试同一业务写入时，复用同一个 `request_id`。

## 5. 批量或 Agent 写入

批量导入、批量出库、库存扣减、批量位置整理和 Agent 自动执行，不要循环调用多个写接口。先创建 workflow plan，检查风险和失败项，再 confirm。

详细流程见 [Workflow 使用指南](WORKFLOW.md)。
