# 后端决策记录

## 范围

第一阶段完成核心闭环 + 完整 CLI：

- 物品 CRUD、归档、移动、数量操作（入库/使用/调整）、补货/常用标记
- 分类管理（树形结构、CRUD）
- 位置管理（树形结构、层级 full_code、CRUD、按位置查物品）
- 全字段搜索（名称/编号/描述/分类/位置/标签/别名/备注/属性/附件名，共 10 个维度）
- 标签管理（CRUD，含删除）
- 别名管理
- 备注记录（含 operator/metadata_json/quantity_change/quantity_after）
- 图片上传、附件上传/下载/删除
- 外部标识绑定（二维码/NFC/条形码）
- 属性模板和物品属性值 CRUD
- 备份创建/列表/恢复/下载（恢复前自动快照）
- API Token 认证（哈希存储）
- 统计概览接口
- 系统信息接口
- 完整 CLI 客户端（覆盖所有 API 能力）
- 关键写接口幂等和轻量审计
- 轻量任务 API（queued/running/succeeded/failed）
- plan / confirm 工作流（批量导入、批量出库、Agent 操作计划）

## 技术选择

- FastAPI
- SQLAlchemy 2.x
- Pydantic / pydantic-settings
- SQLite
- Alembic 管理数据库结构迁移
- Click + httpx（CLI）

## 关键规则

- 物品编号按分类前缀递增，例如 `FIL-000001`。
- 位置 `code/full_code` 第一版创建后不允许修改。
- Token 只存哈希，初始化脚本只显示一次明文 Token。
- 删除物品默认归档；如用户二次确认删除附件，则附件元信息标记删除，并同步删除上传原文件和缩略图文件。
- 删除单个附件时同步释放原文件和缩略图；如果该附件是封面，必须清空物品 `cover_attachment_id`。
- 归档物品禁止库存和位置变更；该限制同时覆盖业务动作接口和通用 `PATCH /items/{id}`。
- 备份恢复前必须先创建当前快照。
- CLI 只调用 API，配置保存在用户目录 `~/.workshop-stash/config.toml`。
- 数据库结构通过 Alembic 迁移固化，默认数据通过 `app.scripts.init_db` 初始化。
- 分类和位置树接口返回嵌套 `children`，前端不需要自行从平铺列表组树。
- 物品列表 API 支持 `page/page_size`，`page_size` 限制为 1 到 100。
- FastAPI 参数校验错误统一返回 `VALIDATION_ERROR`。
- 搜索条件由 `search_service.fulltext_where()` 统一生成，搜索接口和物品列表共用。
- 物品列表支持 `tag` 和 `status` 筛选参数。
- 备注支持 `operator` 和 `metadata_json` 字段，数量操作自动记录变化前后值。
- CLI 客户端支持 `request()`、`upload()`、`download()` 三种操作模式。
- 关键写接口统一使用 `source/module/operator/request_id`，并支持 `Idempotency-Key` 作为 `request_id` 的请求头别名。
- 审计日志只做最小可追踪记录，不做事件溯源；当前覆盖物品创建/更新、库存变化、位置移动和外部标识绑定。
- 工作流遵循先 plan、再 confirm、最后执行；confirm 必须基于已保存的 plan，不重新自由计算输入。
- workflow confirm 的业务写入、plan 状态和任务成功状态应在同一事务内完成；执行失败时回滚业务写入并记录 failed task。
