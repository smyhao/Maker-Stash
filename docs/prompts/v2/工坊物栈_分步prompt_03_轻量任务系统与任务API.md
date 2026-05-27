# 工坊物栈分步 Prompt 03：轻量任务系统与任务 API

## 1. 前提

只有在 Prompt 01 和 Prompt 02 完成后，才执行这一步。  
如果当前关键写接口还没有基本幂等和来源记录，请不要直接开始任务系统。

---

## 2. 目标

本次只做：

```text
为长任务场景提供最小可用的任务系统和稳定任务 API
```

适用场景：

```text
采购数据批量导入
按项目清单批量出库
后续批量处理任务
```

---

## 3. 必做内容

### 3.1 任务模型

至少支持：

```text
queued
running
succeeded
failed
```

并记录：

```text
job_type
input_summary
result_summary
error_message
created_at
started_at
finished_at
source
module
operator
request_id
```

### 3.2 任务 API

至少提供：

```text
提交任务
查询任务详情
查询任务状态
```

### 3.3 稳定任务契约

统一任务相关返回结构和错误结构。

要求：

```text
任务状态字段稳定
任务 ID 明确
失败信息结构清晰
适合未来 SDK 和 CLI 封装
```

---

## 4. 设计边界

本阶段不要做：

```text
分布式队列
多 worker 编排
复杂取消 / 重试策略
完整任务日志中心
```

先做适合个人项目的轻量方案。

---

## 5. 测试要求

至少补这些测试：

```text
任务可成功创建
任务状态可查询
失败任务能返回清晰状态和错误信息
任务 API 返回结构稳定
```

---

## 6. 输出要求

请直接改代码，并输出：

```text
任务模型如何设计
新增了哪些任务 API
为什么当前实现足够轻量
测试结果
后续要交给 dry-run / confirm 的部分
```
