# Workflow 使用指南

Workflow 用于扩展执行高风险写入：批量导入、批量出库、批量位置整理和 Agent 自动操作。它的目标是先预览、再确认、最后执行，并保留任务状态和审计线索。

## 何时必须使用 Workflow

- 一次请求会创建、更新或扣减多条物品记录。
- 操作失败后不应留下半成品。
- Agent 或自动化模块准备修改库存、位置或关键属性。
- 用户需要先看到 creates、updates、skips、failures、risks 再确认。

## 基本流程

1. 创建 plan：

```http
POST /api/workflows/plans
```

请求体必须带来源和幂等字段：

```json
{
  "workflow_type": "batch_outbound",
  "source": "extension",
  "module": "project-outbound",
  "operator": "admin",
  "request_id": "project-outbound-plan-20260528-000001",
  "outbound_rows": [
    {
      "id_or_code": "FIL-000001",
      "amount": 0.12,
      "unit": "kg",
      "note": "项目消耗"
    }
  ]
}
```

2. 检查 plan：

- `failures` 非空时不要 confirm。
- `risks` 非空时需要用户或上层策略确认。
- `creates/updates/skips` 应符合扩展预期。

3. 确认执行：

```http
POST /api/workflows/plans/{plan_id}/confirm
```

```json
{
  "confirm_token": "<confirm-token-from-plan>",
  "source": "extension",
  "module": "project-outbound",
  "operator": "admin",
  "request_id": "project-outbound-confirm-20260528-000001"
}
```

4. 查询任务：

```http
GET /api/tasks/{task_id}/status
```

## 扩展实现要求

- plan 和 confirm 使用不同的 `request_id`。
- confirm 重试时复用同一个 confirm `request_id`。
- confirm 失败时不要自行补写局部结果；先读取 plan/task 状态，再决定是否重新创建 plan。
- 扩展日志至少记录 `workflow_type`、`plan_id`、`task_id`、`request_id` 和 `operator`。

## 不建议的做法

- 不要为了批量写入直接循环调用 `/api/items/{id}/use`。
- 不要在 plan 存在 failures 时自动 confirm。
- 不要跳过 confirm 直接改数据库。
- 不要把 workflow 当作后台队列滥用；单步低风险写入仍可直接调用基础 API。
