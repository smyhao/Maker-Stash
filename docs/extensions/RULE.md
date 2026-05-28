# 扩展开发 Rule

本 rule 约束后续扩展、自动化脚本、Agent 模块，以及为扩展补充主干能力时的开发边界。目标是让扩展增加功能，而不是把主干拖回频繁改业务逻辑的状态。

## 核心原则

- 扩展优先通过 REST API 访问主干；CLI 只作为人工操作、调试和简单脚本入口。
- 扩展不得直连 SQLite，不得绕过 API 修改上传目录，不得依赖前端内部类型、Pinia store、Vue 组件或演示数据。
- 扩展需要能力判断时，先调用 `GET /api/system/capabilities`，不要靠猜测接口或主干版本。
- 单个扩展需要的新能力，不能直接做成扩展专用主干逻辑；确需改主干时，先设计成通用 API 契约。

## 写操作规则

- 所有扩展写操作必须提供 `request_id` 或 `Idempotency-Key`；同一次业务重试必须复用同一个幂等键。
- 扩展写操作应携带 `source/module/operator`：
  - `source` 使用 `extension`、`agent` 或更具体来源。
  - `module` 使用扩展名或模块名。
  - `operator` 使用用户、设备或自动执行身份。
- 扩展错误处理必须依赖稳定的 `error.code`，不要依赖中文 `error.message` 做程序分支。
- 扩展不得通过循环调用多个写接口来模拟批量事务；需要批量或可回滚语义时必须走 workflow。

## API 与 Workflow 选择

- 只读查询可以直接调用基础 API。
- 单步低风险写入可以直接调用基础 API，但必须带幂等键和来源字段。
- 批量导入、批量出库、库存扣减、批量位置整理、Agent 自动执行等高风险写入，必须优先走 `plan -> confirm -> task` workflow。
- Workflow plan 阶段发现 failures 时，不要 confirm；需要先修正输入或让用户确认处理方式。

## 修改主干时的规则

- 新增或变更可被扩展依赖的接口时，必须同步更新 `docs/extensions/API.md`。
- 新增扩展可见能力时，必须同步更新 `GET /api/system/capabilities` 的功能或限制字段。
- 新增稳定错误码时，必须写入扩展 API 文档；同一 `api_version` 下不要改名已有稳定错误码。
- 主干改动必须补对应测试，至少覆盖接口 envelope、关键字段和失败语义。
- 不为单个扩展引入复杂平台能力，例如扩展注册中心、独立服务、消息队列或 SDK；除非已经有多个真实扩展共同需要。

## 验收要求

扩展相关主干改动完成后，至少运行：

```powershell
cd backend
& ..\.venv\Scripts\python.exe -m pytest
& ..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
cd ..\frontend
npm.cmd run build
```

如果只修改独立扩展代码，至少验证该扩展的 API 调用、幂等重试、错误处理和 workflow 分支。
