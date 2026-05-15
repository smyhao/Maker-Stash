# Maker Stash / 工坊物栈

面向个人工坊的轻量化资源管理系统，管理元器件、3D 耗材、工具、备用材料、线材等物料。

## 功能

- 物品管理（CRUD、数量追踪、状态管理）
- 分类管理（树形结构，自动编号前缀）
- 位置管理（层级位置，full_code 编号）
- 搜索（名称/编号/标签/别名/备注/属性模糊匹配）
- 标签 & 别名
- 自定义属性（分类字段模板 + 物品属性值）
- 图片 & 附件上传
- 备份 & 恢复
- API Token 认证
- CLI 命令行客户端
- REST API

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / SQLAlchemy 2.x / SQLite |
| 前端 | Vue 3 / TypeScript / Vite / Pinia / Tailwind CSS |
| CLI | Click，纯 API 调用 |

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 18+

### 安装

```bash
# 后端依赖
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt   # Windows
# .venv/bin/python -m pip install -r backend/requirements.txt     # Linux/macOS

.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
.venv/Scripts/python -m app.scripts.init_db
.venv/Scripts/python -m app.scripts.create_token --name cli

# 前端依赖
cd frontend && npm install
```

### 启动

```bash
python start.py
```

- 后端: http://127.0.0.1:8000
- 前端: http://127.0.0.1:5173

更多启动参数见 [START.md](START.md)。

### 关闭

```bash
python stop.py
```

## 项目结构

```
backend/
  app/             后端应用（API / Service / Model / CLI）
  alembic/         数据库迁移
  tests/           测试
frontend/
  src/             前端应用
prompt/start/      设计规范文档
```

## CLI 用法

```bash
# 配置
python -m app.cli.main config set api_url http://127.0.0.1:8000
python -m app.cli.main config set token <your-token>

# 物品
python -m app.cli.main item list
python -m app.cli.main item add --name "黑色 PLA" --category filament --quantity 0.42 --unit kg
python -m app.cli.main item use FIL-000001 --amount 0.12 --unit kg
python -m app.cli.main search PLA --json

# 备份
python -m app.cli.main backup create
python -m app.cli.main backup list
```

详细设计规范见 `prompt/start/` 目录。

## License

MIT
