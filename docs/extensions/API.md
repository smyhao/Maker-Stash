# 扩展 API 调用规范

本文档面向后续扩展、自动化脚本和 Agent 模块。主干默认作为稳定后端底座，扩展优先通过 REST API 接入；CLI 主要用于人工操作、调试和简单脚本。

## 接入边界

- 扩展必须通过 `/api` REST 接口访问主干，不要直连 SQLite，也不要绕过 API 直接修改上传目录。
- 扩展不要依赖前端内部类型、Pinia store、Vue 组件或本地演示数据。
- CLI 可以作为人工入口或一次性脚本入口；长期运行、批量写入和 Agent 操作应直接调用 REST API。
- 扩展启动时可以调用 `GET /api/system/capabilities` 判断主干版本、功能开关和限制值。

## 认证与请求

所有业务 API 默认需要 Bearer Token：

```http
Authorization: Bearer <token>
```

扩展应把 API 地址和 Token 放在自己的配置中，不要写入源码。Token 明文只在创建时显示一次，丢失后应创建新 Token。

写操作必须提供幂等键，优先使用请求体 `request_id`；如果请求体不方便携带，可使用请求头：

```http
Idempotency-Key: extension-name-operation-unique-id
```

建议所有扩展写操作同时携带来源字段：

```json
{
  "source": "extension",
  "module": "scanner-importer",
  "operator": "admin",
  "request_id": "scanner-importer-20260528-000001"
}
```

- `source`：调用来源，扩展通常使用 `extension`；Agent 可使用 `agent`。
- `module`：扩展名或模块名，用于审计和排错。
- `operator`：用户、设备或自动执行身份。
- `request_id`：单次业务写入的唯一 ID，重试时保持不变。

## 直接 API 与 Workflow 选择

可以直接调用基础 API 的场景：

- 查询物品、分类、位置、标签、附件、统计信息。
- 单个物品的低风险写入，例如编辑名称、移动一次位置、上传一个附件。
- 单步写入仍需提供幂等键和来源字段。

应优先使用 `plan -> confirm -> task` workflow 的场景：

- 批量导入、批量出库、批量整理位置。
- Agent 自动执行的库存、位置或附件变更。
- 任何中途失败后不应留下半成品的操作。
- 需要先展示风险、失败项或预览结果再确认的操作。

## 能力发现

扩展应使用：

```http
GET /api/system/capabilities
```

响应使用统一 envelope：

```json
{
  "success": true,
  "data": {
    "app": "workshop-stash",
    "version": "0.1.0",
    "api_version": "0.1",
    "features": {
      "items": true,
      "categories": true,
      "locations": true,
      "attachments": true,
      "containers": true,
      "search": true,
      "backups": true,
      "tokens": true,
      "idempotency": true,
      "audit": true,
      "tasks": true,
      "workflow_plan_confirm": true
    },
    "limits": {
      "max_upload_bytes": 52428800,
      "page_size_max": 100
    },
    "extension_contract": {
      "preferred_interface": "rest_api",
      "write_idempotency_required": true,
      "workflow_required_for_bulk_or_agent_writes": true
    }
  },
  "message": "ok"
}
```

Capabilities 不返回 `database_url`、`upload_dir`、`backup_dir` 等本地路径。需要管理诊断信息时使用 `/api/system/info`，扩展不要依赖这些本地字段。

## 扩展 UI 声明

主干支持通过 `extensions/*/extension.json` 发现扩展 UI 声明。manifest 可以声明：

- `settings.schema`：扩展配置表单字段。
- `contributions`：扩展希望显示在主干界面的按钮、菜单或操作入口。

扩展 UI 管理接口：

```http
GET /api/extensions
PATCH /api/extensions/{extension_id}
GET /api/extensions/{extension_id}/settings
PATCH /api/extensions/{extension_id}/settings
GET /api/extensions/contributions?place=item.detail.actions
POST /api/extensions/{extension_id}/actions/{action}
```

当前支持的配置字段类型：

```text
string
number
boolean
select
multiselect
secret
path
```

当前建议优先使用的 contribution 位置：

```text
settings.extensions
item.detail.actions
item.list.bulk_actions
tools.menu
```

注意：UI 声明只负责让主干显示配置和入口。扩展 action 的真实执行器需要后续单独接入；未接入时主干会返回 `EXTENSION_ACTION_NOT_IMPLEMENTED`。

## 错误处理与版本策略

失败响应统一为：

```json
{
  "success": false,
  "error": {
    "code": "ITEM_NOT_FOUND",
    "message": "物品不存在"
  }
}
```

扩展应依赖 `error.code`，不要依赖中文 `error.message`。`message` 可用于日志或界面提示，但不作为程序分支依据。

稳定错误码类别：

- 认证与权限：`INVALID_TOKEN`
- 参数校验：`VALIDATION_ERROR`
- 资源不存在：`ITEM_NOT_FOUND`、`CATEGORY_NOT_FOUND`、`LOCATION_NOT_FOUND`、`BACKUP_NOT_FOUND`、`TASK_NOT_FOUND`、`PLAN_NOT_FOUND`
- 业务规则：`NEGATIVE_QUANTITY_NOT_ALLOWED`、`ARCHIVED_ITEM_MOVE_FORBIDDEN`、`ARCHIVED_ITEM_QUANTITY_FORBIDDEN`、`SLOT_OCCUPIED`
- 上传与附件：`UPLOAD_TOO_LARGE`、`UPLOAD_FAILED`、`ATTACHMENT_NOT_FOUND`
- 备份与任务：`BACKUP_IN_PROGRESS`
- Workflow：`UNSUPPORTED_WORKFLOW_TYPE`、`PLAN_CONFIRM_TOKEN_INVALID`、`PLAN_HAS_FAILURES`
- 扩展 UI：`EXTENSION_NOT_FOUND`、`EXTENSION_DISABLED`、`EXTENSION_ACTION_NOT_FOUND`、`EXTENSION_ACTION_NOT_IMPLEMENTED`

兼容策略：

- 已公开的稳定错误码不随意改名。
- 可以新增错误码，扩展默认应把未知错误码按普通失败处理。
- 破坏性 API 变化必须提高 `api_version`。
- 同一 `api_version` 下，字段只做兼容新增，不删除或改变既有含义。
