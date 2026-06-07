# 扩展开发规范与方法

本文档说明 Maker Stash 扩展的开发方式、接入边界和验收要求。开发扩展或为扩展补充主干能力时，必须同时遵守 [扩展开发 Rule](RULE.md)。

## 适用范围

这里的扩展包括但不限于：

- 扫码、标签打印、批量导入、批量出库等本地工具。
- Agent 自动化、外部脚本、定时任务或设备联动模块。
- 通过 `extensions/*/extension.json` 接入主干界面的扩展 UI 声明。
- 为多个扩展提供通用能力的主干 API、workflow 或 capability 改动。

不属于扩展的内容：

- 主干业务页面的普通功能迭代。
- 只在前端内部使用、不会被外部模块依赖的组件改动。
- 一次性人工维护命令，除非它会长期作为扩展入口运行。

## 开发前判断

开始编码前先明确以下问题：

1. 这个能力能否只通过现有 REST API 完成。
2. 写操作是单步低风险，还是批量、高风险、Agent 自动执行。
3. 是否需要在主干界面显示配置或操作入口。
4. 是否需要主干新增通用 API、错误码、capability 或 workflow 类型。

推荐决策：

- 只读查询：直接调用基础 API。
- 单个物品、单次移动、单个附件等低风险写入：直接调用基础 API，但必须带幂等键和来源字段。
- 批量导入、批量出库、库存扣减、批量位置整理、Agent 自动写入：使用 `plan -> confirm -> task` workflow。
- 只有一个扩展需要的特殊能力：优先放在扩展内部，不要改主干。
- 多个扩展会共同依赖的能力：先设计稳定 API 契约，再改主干。

## 扩展目录

扩展放在项目根目录的 `extensions/` 下，每个扩展一个子目录：

```text
extensions/
  scanner-importer/
    extension.json
    README.md
    src/
    tests/
```

当前主干会扫描：

```text
extensions/*/extension.json
```

扩展目录名建议和 `extension.json` 的 `id` 保持一致。扩展代码可以使用自己的语言和依赖管理方式，但不得依赖前端内部类型、Pinia store、Vue 组件或演示数据。

如果扩展需要接入主干前端，扩展自身页面、API 调用封装、解析逻辑和测试代码仍应放在对应扩展目录下，例如 `extensions/<extension-id>/src/`。主干前端只保留通用挂载所需的最小入口，例如路由懒加载、菜单入口或扩展容器；不要把单个扩展的业务页面长期放进 `frontend/src/views` 或把扩展专用 API 封装放进 `frontend/src/api`。

有前端页面的扩展应在自身目录提供：

```text
extensions/<extension-id>/src/index.ts
```

该文件默认导出扩展入口 Vue 组件。主干前端通过通用 `/extensions/<extension-id>` 路由加载该入口。需要出现在管理页“扩展工具”区域时，在 manifest 中声明 `place: "tools.menu"`，并使用 `open-*` 形式的 action。

## Manifest 规范

`extension.json` 用于声明扩展基础信息、配置项和主干 UI 入口。最小示例：

```json
{
  "id": "scanner-importer",
  "name": "扫码入库",
  "description": "通过扫码设备快速录入耗材",
  "version": "0.1.0",
  "api_version": "0.1",
  "settings": {
    "schema": {
      "device_id": {
        "type": "string",
        "label": "设备 ID",
        "required": true
      },
      "api_token": {
        "type": "secret",
        "label": "API Token",
        "required": true
      }
    }
  },
  "contributions": [
    {
      "place": "item.detail.actions",
      "type": "button",
      "label": "扫码补货",
      "action": "scan-restock",
      "requires": ["items"]
    }
  ]
}
```

字段要求：

- `id` 必须使用小写字母、数字和短横线，长度 3 到 64，首尾必须是字母或数字。
- `version` 使用语义化版本，扩展自身破坏性变更需要提高主版本。
- `api_version` 表示扩展依赖的主干 API 契约版本。
- `settings.schema` 只声明主干需要渲染和保存的本机配置。
- `contributions` 只声明界面入口，不代表 action 执行器已经可用。

当前支持的设置类型：

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

其中 `item.detail.actions` 已有前端插槽；其他位置属于后续扩展 UI 契约方向，使用前需要确认主干页面是否已经挂载对应插槽。

注意：当前主干可以展示扩展配置和入口，但 `/api/extensions/{extension_id}/actions/{action}` 的真实执行器尚未接入。未接入时会返回 `EXTENSION_ACTION_NOT_IMPLEMENTED`。如果扩展需要立即执行业务逻辑，应由扩展自身服务或脚本调用主干 REST API。

## API 接入规则

扩展必须通过 `/api` REST 接口访问主干：

- 不得直连 SQLite。
- 不得绕过 API 修改上传目录、备份目录或附件文件。
- 不得调用未公开的后端函数作为长期接口。
- 不得依赖中文错误消息做程序分支。

扩展启动时先调用：

```http
GET /api/system/capabilities
```

至少检查：

- `api_version` 是否在扩展支持范围内。
- 所需 `features` 是否为 `true`。
- 上传类扩展是否遵守 `limits.max_upload_bytes`。
- 高风险写入是否遵守 `extension_contract.workflow_required_for_bulk_or_agent_writes`。

所有业务 API 默认使用 Bearer Token：

```http
Authorization: Bearer <token>
```

Token、API 地址、设备 ID、路径和外部服务密钥必须放在扩展配置或运行环境中，不要写入源码。

## 写操作规范

所有扩展写操作必须携带幂等键，优先使用请求体 `request_id`。如果请求体不方便携带，可使用请求头 `Idempotency-Key`。

同一次业务重试必须复用同一个幂等键。不要在网络失败后生成新的 `request_id`，否则可能造成重复写入。

写操作应携带来源字段：

```json
{
  "source": "extension",
  "module": "scanner-importer",
  "operator": "device-01",
  "request_id": "scanner-importer-add-20260605-000001"
}
```

字段含义：

- `source`：调用来源，扩展通常使用 `extension`，Agent 使用 `agent`。
- `module`：扩展名或模块名。
- `operator`：用户、设备、服务账号或自动执行身份。
- `request_id`：单次业务写入的唯一 ID。

当同时提供请求体 `request_id` 和请求头 `Idempotency-Key` 时，两者必须一致。

## Workflow 使用要求

以下场景必须优先使用 workflow：

- 一次请求会创建、更新或扣减多条记录。
- 失败后不应留下半成品。
- Agent 或自动化模块准备修改库存、位置或关键属性。
- 需要先展示 creates、updates、skips、failures、risks，再由用户或上层策略确认。

基本流程：

1. `POST /api/workflows/plans` 创建 plan。
2. 检查 plan 的 `failures`、`risks`、`creates`、`updates`、`skips`。
3. `failures` 非空时不要 confirm。
4. `POST /api/workflows/plans/{plan_id}/confirm` 确认执行。
5. `GET /api/tasks/{task_id}/status` 查询任务状态。

实现要求：

- plan 和 confirm 使用不同的 `request_id`。
- confirm 重试时复用同一个 confirm `request_id`。
- confirm 失败后先读取 plan/task 状态，不要自行补写局部结果。
- 扩展日志记录 `workflow_type`、`plan_id`、`task_id`、`request_id`、`operator`。

## 错误处理

扩展必须按统一 envelope 解析响应：

```json
{
  "success": false,
  "error": {
    "code": "ITEM_NOT_FOUND",
    "message": "物品不存在"
  }
}
```

程序分支只能依赖 `error.code`。`error.message` 只用于日志或界面提示，因为中文文案可能调整。

处理未知错误码时，扩展应按普通失败处理并记录完整响应，不要假设未知错误可以安全忽略。

## 主干改动规则

只有当多个扩展会共同依赖某个能力，或现有 REST API 无法安全表达该能力时，才应改主干。

改主干时必须同步完成：

- 新增或变更扩展可依赖接口：更新 [API 调用规范](API.md)。
- 新增扩展可见能力或限制：更新 `GET /api/system/capabilities`。
- 新增稳定错误码：写入 [API 调用规范](API.md)。
- 新增高风险写入形态：优先设计 workflow 契约，并更新 [Workflow 使用指南](WORKFLOW.md)。
- 后端接口改动：补测试，至少覆盖 envelope、关键字段、失败语义和幂等行为。

不要为单个扩展引入复杂平台能力，例如扩展注册中心、独立服务、消息队列或 SDK。确实需要时，先确认已经有多个真实扩展共同需要。

## 测试与验收

独立扩展至少验证：

- 能读取配置并连接主干。
- 能读取 `GET /api/system/capabilities` 并按能力开关分支。
- 只读 API 调用能正确解析成功 envelope。
- 写操作包含 `request_id` 或 `Idempotency-Key`。
- 同一写操作重试不会重复写入。
- 错误处理依赖 `error.code`。
- 批量或 Agent 写入走 workflow，且 `failures` 非空时不会 confirm。

扩展相关主干改动完成后，至少运行：

```powershell
cd backend
& ..\.venv\Scripts\python.exe -m pytest
& ..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
cd ..\frontend
npm.cmd run build
```

如果只修改文档，可以不运行测试，但需要检查链接、术语和现有实现是否一致。

## 开发清单

开始前：

- 明确扩展类型、写入风险和是否需要 UI 声明。
- 阅读 [扩展开发 Rule](RULE.md)、[API 调用规范](API.md) 和 [Workflow 使用指南](WORKFLOW.md)。
- 确认现有 API 是否足够，不足时先设计通用契约。

实现中：

- 使用 REST API，不直连数据库或上传目录。
- 所有写操作携带幂等键和来源字段。
- 高风险写入使用 workflow。
- 日志记录 request、operator、目标资源和稳定错误码。
- 只修改与当前扩展目标直接相关的文件。

交付前：

- 验证扩展配置、capabilities、API 调用和错误处理。
- 验证幂等重试。
- 验证 workflow plan/confirm/task 分支。
- 如果改主干，同步文档、capabilities、错误码和测试。
