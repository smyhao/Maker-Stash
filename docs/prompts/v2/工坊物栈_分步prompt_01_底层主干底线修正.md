# 工坊物栈分步 Prompt 01：底层主干底线修正

## 1. 目标

本次只做第一步，不讨论任务系统、审计系统、dry-run、工作流层。  
本次目标是：

```text
修复后端底层主干的基础风险，让数据边界和演进方式先稳定下来
```

---

## 2. 必做内容

### 2.1 数据完整性

修复并验证：

```text
- SQLite foreign key 必须真正开启
- 写接口不得写入不存在的 category / location / item 等引用
- identifier 绑定必须保持唯一
```

重点检查：

```text
app/core/database.py
app/services/item_service.py
app/services/location_service.py
app/services/category_service.py
app/services/metadata_service.py
```

### 2.2 库存和归档边界

请明确并落实：

```text
- 默认不允许负库存
- use / add / adjust 输入要做合理校验
- 归档物品后禁止继续执行库存变更和位置变更
```

### 2.3 迁移方式

修正数据库结构管理方式：

```text
- 应用启动时不再隐式 create_all()
- 数据库结构只通过 Alembic 迁移维护
- 初始化逻辑和迁移逻辑分开
```

### 2.4 基础 API 契约收口

先修复现有明显漂移，而不是做全面接口重设计。

至少处理：

```text
- CLI 与后端 schema 的明显不一致
- attr-def update 等已知契约漂移
```

---

## 3. 测试要求

至少补这些测试：

```text
- foreign key 已开启
- 不存在引用会返回明确错误
- 负库存被拒绝
- 归档物品不能继续关键写操作
- 关键 CLI / API 契约已对齐
```

---

## 4. 明确不做

```text
不做幂等
不做审计
不做任务系统
不做 dry-run / confirm
不做中间层工作流
不做 SDK
```

---

## 5. 输出要求

请直接改代码，并输出：

```text
本次改了什么
为什么这一步必须先做
测试结果
仍然存在但留给下一步的问题
```
