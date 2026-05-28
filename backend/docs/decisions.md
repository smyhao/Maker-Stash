# 后端决策记录

## 范围

第一阶段完成核心闭环 + 完整 CLI：

- 物品 CRUD、归档、移动、数量操作（入库/使用/调整）、补货/常用标记
- 分类管理（树形结构、CRUD）
- 位置管理（树形结构、层级 full_code、CRUD、按位置查物品、可视化收纳盒/格位）
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
- 前端附件区只隐藏当前封面资产，避免封面重复显示；普通附件入口上传的图片仍作为资料附件展示。
- 归档物品禁止库存和位置变更；该限制同时覆盖业务动作接口和通用 `PATCH /items/{id}`。
- 备份恢复前必须先创建当前快照。
- CLI 只调用 API，配置保存在用户目录 `~/.workshop-stash/config.toml`。
- 数据库结构通过 Alembic 迁移固化，默认数据通过 `app.scripts.init_db` 初始化。
- 分类和位置树接口返回嵌套 `children`，前端不需要自行从平铺列表组树。
- 分类筛选和搜索筛选按分类分支处理：父分类包含所有子孙分类物品；分类统计也会把子孙分类数量汇总到父分类。
- 分类可调整父级，但必须拒绝移动到自身或子分类下，避免形成循环树。
- 可视化收纳盒是普通位置的扩展形态，支持 `grid` 与 `row`，自动格位不在普通位置树中展开。
- 收纳盒外观颜色保存为预设名或 `#RRGGBB` RGB 编号，作为前端识别色元数据，不影响业务规则。
- 一个自动格位首版最多绑定一条未归档物品记录；空格位可通过物品移动接口放入已有物品，移动到已占格位返回冲突，格位间交换使用专用原子接口并写入双方记录。
- 物品列表 API 支持 `page/page_size`，`page_size` 限制为 1 到 100。
- FastAPI 参数校验错误统一返回 `VALIDATION_ERROR`。
- 搜索条件由 `search_service.fulltext_where()` 统一生成，搜索接口和物品列表共用。
- 前端全局搜索建议复用 `/api/items?q=`，点击建议后切到库存页并选中物品。
- 物品列表支持 `tag` 和 `status` 筛选参数。
- 备注支持 `operator` 和 `metadata_json` 字段，数量操作自动记录变化前后值。
- CLI 客户端支持 `request()`、`upload()`、`download()` 三种操作模式。
- 关键写接口统一使用 `source/module/operator/request_id`，并支持 `Idempotency-Key` 作为 `request_id` 的请求头别名。
- 审计日志只做最小可追踪记录，不做事件溯源；当前覆盖物品创建/更新、库存变化、位置移动、格位交换和外部标识绑定。
- 工作流遵循先 plan、再 confirm、最后执行；confirm 必须基于已保存的 plan，不重新自由计算输入。
- workflow confirm 的业务写入、plan 状态和任务成功状态应在同一事务内完成；执行失败时回滚业务写入并记录 failed task。
