# CLAUDE.md

## 项目概述

工坊物栈 (Maker Stash) — 面向个人工坊的轻量化智能化资源管理系统，管理元器件、3D 耗材、工具、线材等物料。

## 技术栈

- **后端**: Python 3.12+ / FastAPI / SQLAlchemy 2.x / SQLite / Alembic / Pydantic
- **前端**: Vue 3 + TypeScript / Vite / Pinia / Tailwind CSS / Lucide 图标
- **CLI**: Click + httpx，纯 API 调用，不直连数据库

## 项目结构

```
backend/
  app/
    api/routes/     路由层，只处理请求/响应（items, categories, locations, search, metadata, attributes, attachments, backups, health, stats）
    core/           配置、数据库、安全、统一响应
    models/         SQLAlchemy 数据模型
    schemas/        Pydantic 请求/响应 Schema
    services/       业务逻辑层（item_service, search_service, category_service, location_service, attribute_service, metadata_service, file_service, backup_service）
    repositories/   数据访问层
    cli/            CLI 客户端（client.py 含 upload/download 支持）
    scripts/        初始化脚本
  alembic/          数据库迁移
  tests/            pytest 测试（25 个）

frontend/
  src/
    api/            API 封装（axios）
    components/     组件（layout/panels/dialogs/ui）
    stores/         Pinia 状态管理
    views/          页面
    types/          TypeScript 类型

docs/
  START.md          启动和局域网部署说明
  prompts/          历史 prompt / 设计资料
config/
  start.example.toml 启动器配置示例
```

## 开发命令

```bash
# 启动（一键）
python start.py

# 后端单独启动
cd backend && ../.venv/Scripts/python.exe -m uvicorn app.main:app --reload

# 前端单独启动
cd frontend && npm run dev

# 后端测试
cd backend && ../.venv/Scripts/python.exe -m pytest

# CLI
cd backend && ../.venv/Scripts/python.exe -m app.cli.main --help
```

## 架构规范

1. **API First**: 所有核心能力必须先有 API，前端和 CLI 都是 API 客户端
2. **分层**: Router → Service → Repository → Database/Files
3. **Router 层不写业务逻辑**，只做参数校验和响应封装
4. **CLI 不直连数据库**，统一调用 API
5. **统一响应**: `{ success, data, message }` 或 `{ success, error: { code, message } }`
6. **错误码大写蛇形**: `ITEM_NOT_FOUND`, `VALIDATION_ERROR`, `DUPLICATE_CODE`

## 数据模型

13 个核心表: Item, Category, Location, Tag/ItemTag, Alias, Note, Attachment, Identifier, AttributeDefinition/ItemAttributeValue, Backup, ApiToken, SystemSetting

物品编号格式: `{PREFIX}-{000001}`（如 FIL-000001）
位置编号格式: `WS.CAB-A.S02.G03`（层级 full_code）

## 搜索

全字段搜索逻辑在 `services/search_service.py` 的 `fulltext_where()` 函数，搜索和物品列表共用。

覆盖 10 个维度：名称、编号、描述、分类(name/slug)、位置(name/full_code)、标签、别名、备注、属性(name/value)、附件名。

`/api/search` 支持额外过滤：`category`、`location`、`tag`、`include_archived`。

`/api/items` 的 `q` 参数使用同样的全字段搜索。

搜索结果返回 `matched_by` 标记命中维度。

## CLI 命令

完整命令组：`item`, `category`, `location`, `tag`, `attr-def`, `backup`, `system`, `search`, `config`, `ping`, `image-add`, `file-add`, `file-list`, `file-delete`

`item` 子命令：`list`, `show`, `add`, `update`, `delete`, `move`, `add-qty`, `use`, `adjust`, `restock`, `unstock`, `favorite`, `unfavorite`, `tag`, `untag`, `alias`, `unalias`, `bind`, `unbind`, `find-id`, `notes`, `add-note`

CLI 客户端支持 `request()`, `upload()`, `download()` 三种操作。

## 设计文档

历史设计资料见 `docs/prompts/` 目录。

## 注意事项

- 数据库默认 SQLite，路径 `backend/data/db.sqlite3`
- 上传文件存在 `backend/data/uploads/`
- 备份存在 `backend/data/backups/`
- 删除物品默认软删除（is_archived=True）
- 位置 code/full_code 创建后不建议修改
- API Token 校验默认开启，测试时关闭
- 前端 vite.config.ts 已配置 `/api` 代理到后端 8000 端口
- Notes 支持 operator 和 metadata_json 字段，所有数量操作自动记录 quantity_change/quantity_after
