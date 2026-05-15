# CLAUDE.md

## 项目概述

工坊物栈 (Maker Stash) — 面向个人工坊的轻量化资源管理系统，管理元器件、3D 耗材、工具、线材等物料。

## 技术栈

- **后端**: Python 3.12+ / FastAPI / SQLAlchemy 2.x / SQLite / Alembic / Pydantic
- **前端**: Vue 3 + TypeScript / Vite / Pinia / Tailwind CSS / Lucide 图标
- **CLI**: Click，纯 API 调用，不直连数据库

## 项目结构

```
backend/
  app/
    api/routes/     路由层，只处理请求/响应
    core/           配置、数据库、安全、统一响应
    models/         SQLAlchemy 数据模型
    schemas/        Pydantic 请求/响应 Schema
    services/       业务逻辑层
    repositories/   数据访问层
    cli/            CLI 客户端
    scripts/        初始化脚本
  alembic/          数据库迁移
  tests/            pytest 测试

frontend/
  src/
    api/            API 封装（axios）
    components/     组件（layout/panels/dialogs/ui）
    stores/         Pinia 状态管理
    views/          页面
    types/          TypeScript 类型

prompt/start/       设计规范文档
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

## 设计文档

详细设计规范见 `prompt/start/` 目录下的三个文档。

## 注意事项

- 数据库默认 SQLite，路径 `backend/data/db.sqlite3`
- 上传文件存在 `backend/data/uploads/`
- 备份存在 `backend/data/backups/`
- 删除物品默认软删除（is_archived=True）
- 位置 code/full_code 创建后不建议修改
- API Token 校验默认开启，测试时关闭
- 前端 vite.config.ts 已配置 `/api` 代理到后端 8000 端口
