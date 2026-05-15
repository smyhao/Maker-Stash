# Maker Stash / 工坊物栈

面向个人工坊的轻量化智能化资源管理系统。

管理你的元器件、3D 打印耗材、工具、备用材料、线材等物料 —— 知道有什么、放在哪、还剩多少。

---

## 为什么做这个

创客/个人工坊的常见问题：

- 一堆元器件、耗材、工具，找不到东西放哪了
- 不记得某卷 PLA 还剩多少，打开才发现用完了
- 同一个东西有多个叫法，搜不到
- 手机拍了照片但没和物品关联起来
- 搬过几次之后位置全乱了

工坊物栈解决这些问题，但不做工厂化的事：没有入库单/出库单/审批/采购/供应商管理。

核心理念：

```
快速记录 · 快速查找 · 灵活修改 · 位置清楚 · API 可调用
```

---

## 功能一览

### 物品管理

- 新增/编辑/归档物品，自动生成编号（如 `FIL-000001`）
- 数量追踪：入库、使用、直接调整，自动记录变化
- 状态标记：正常、少量、已用完、损坏、找不到、闲置
- 补货标记：一键标记需要补货的物品
- 常用收藏：快速找到常用物品

### 分类 & 位置

- **分类**：树形结构，每个分类有编号前缀（元器件=ELE、3D耗材=FIL、工具=TOOL 等）
- **位置**：层级位置编号系统（如 `WS.CAB-A.S02.G03` = 工坊.A柜.第二层.03格）
- 位置树可视化，按位置筛选物品

### 搜索

全字段模糊搜索，输入不完整关键词也能找到：

```
esp     → ESP32-S3 模块（匹配名称、别名）
pla     → 黑色 PLA、白色 PLA+（匹配名称、标签）
乐鑫    → ESP32-S3 模块（匹配标签/别名）
WS.DRY  → 干燥箱下的所有物品（匹配位置编号）
```

搜索范围：名称、编号、分类、标签、别名、位置、备注、自定义属性、附件名。

### 标签 & 别名

- 给物品打标签，自由筛选
- 别名增强搜索：ESP32-S3 可以有别名「开发板」「乐鑫」「WiFi模块」

### 自定义属性

不同分类的物品有不同的属性需求。通过分类字段模板 + 物品属性值实现：

```
黑色 PLA：     材质=PLA  颜色=黑色  线径=1.75mm  净重=1kg
ESP32-S3：    型号=ESP32-S3  Flash=4MB  通信=Wi-Fi+BLE
精密螺丝刀：  头型=十字/一字  规格=PH1/PH2
```

### 图片 & 附件

- 上传物品照片、Datasheet、说明书、发票等
- 支持设置封面图
- 文件存本地目录，数据库只存元信息

### 备份 & 恢复

- 一键创建备份（数据库 + 上传文件）
- 恢复前自动创建当前快照，防止误恢复
- 支持下载备份文件

### API Token 认证

- 所有 API 通过 Bearer Token 认证
- 支持多个 Token（CLI、AI 助手、扫码模块等各自独立）
- Token 只存哈希，不存明文

### CLI 命令行

完整的命令行客户端，所有操作都可以通过 CLI 完成：

```bash
stash item list                              # 列出物品
stash item add --name "黑色 PLA" --category filament
stash item use FIL-000001 --amount 0.12      # 使用消耗
stash item move FIL-000001 --to WS.DRY-A.G03 # 移动位置
stash search PLA --json                      # 搜索并输出 JSON
stash backup create                          # 创建备份
```

---

## 技术架构

```
Vue 前端  ──→  REST API  ──→  Service 业务层  ──→  Repository  ──→  SQLite + 文件系统
CLI 客户端 ──→  REST API  ──→  （同上）
外部模块   ──→  REST API  ──→  （同上）
```

所有客户端统一通过 API 访问，不直连数据库。

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / SQLAlchemy 2.x / SQLite / Alembic / Pydantic |
| 前端 | Vue 3 / TypeScript / Vite / Pinia / Tailwind CSS / Lucide 图标 |
| CLI | Click + httpx，纯 API 调用 |
| 数据库 | SQLite（轻量，单文件，适合个人部署） |

### 后端分层

```
backend/app/
├── api/routes/       路由层 — 只处理请求参数和响应
├── core/             配置、数据库、安全、统一响应、错误处理
├── models/           SQLAlchemy 数据模型（13 个表）
├── schemas/          Pydantic 请求/响应结构
├── services/         业务逻辑层
├── repositories/     数据访问层
├── cli/              CLI 客户端
└── scripts/          初始化脚本
```

### 数据模型

13 个核心表，覆盖物品管理全流程：

```
items                    物品主表
categories               分类（树形，带编号前缀）
locations                位置（树形，带层级 full_code）
tags + item_tags         标签 + 多对多关联
aliases                  物品别名（增强搜索）
notes                    备注和操作记录
attachments              图片和附件元信息
identifiers              外部标识（二维码/NFC/条形码）
attribute_definitions    分类字段模板
item_attribute_values    物品自定义属性值
backups                  备份记录
api_tokens               API Token（哈希存储）
system_settings          系统配置
```

### 编号规则

**物品编号** — 按分类前缀自增：

```
ELE-000001      元器件
FIL-000001      3D 打印耗材
TOOL-000001     工具
MAT-000001      备用材料
CAB-000001      线材
OTH-000001      其他
```

**位置编号** — 层级 full_code：

```
WS              工坊
WS.CAB-A        工坊 → A柜
WS.CAB-A.S02    工坊 → A柜 → 第二层
WS.CAB-A.S02.G03  工坊 → A柜 → 第二层 → 03格
```

---

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 18+

### 安装

```bash
# 1. 创建虚拟环境并安装后端依赖
python -m venv .venv

# Windows:
.venv\Scripts\python -m pip install -r backend\requirements.txt
.venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
.venv\Scripts\python -m app.scripts.init_db
.venv\Scripts\python -m app.scripts.create_token --name cli

# Linux/macOS:
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python -m app.scripts.init_db
.venv/bin/python -m app.scripts.create_token --name cli

# 2. 安装前端依赖
cd frontend && npm install && cd ..
```

`create_token` 会显示一个明文 Token，只显示一次，记下来。

### 启动

```bash
# 一键启动（后端 + 前端）
python start.py
```

启动后：
- 后端 API: http://127.0.0.1:8000
- 前端页面: http://127.0.0.1:5173（自动打开浏览器）

首次使用在前端「设置」里填入 API 地址和 Token。

更多启动参数见 [START.md](START.md)。

### 关闭

```bash
python stop.py
```

---

## CLI 用法

```bash
cd backend

# 配置连接
../.venv/Scripts/python -m app.cli.main config set api_url http://127.0.0.1:8000
../.venv/Scripts/python -m app.cli.main config set token <your-token>

# 测试连接
../.venv/Scripts/python -m app.cli.main ping

# 物品管理
../.venv/Scripts/python -m app.cli.main item list
../.venv/Scripts/python -m app.cli.main item list --json
../.venv/Scripts/python -m app.cli.main item show FIL-000001
../.venv/Scripts/python -m app.cli.main item add --name "黑色 PLA" --category filament --quantity 0.42 --unit kg
../.venv/Scripts/python -m app.cli.main item use FIL-000001 --amount 0.12 --unit kg --note "打印外壳"
../.venv/Scripts/python -m app.cli.main item adjust FIL-000001 --quantity 0.30 --unit kg
../.venv/Scripts/python -m app.cli.main item move FIL-000001 --to WS.DRY-A.G03
../.venv/Scripts/python -m app.cli.main item restock FIL-000001
../.venv/Scripts/python -m app.cli.main item favorite FIL-000001

# 标签和别名
../.venv/Scripts/python -m app.cli.main item tag ELE-000001 乐鑫 开发板
../.venv/Scripts/python -m app.cli.main item alias ELE-000001 WiFi模块

# 外部标识（二维码/NFC）
../.venv/Scripts/python -m app.cli.main item bind ELE-000001 --type qrcode --value QR-ELE-000001
../.venv/Scripts/python -m app.cli.main item find-id QR-ELE-000001

# 位置管理
../.venv/Scripts/python -m app.cli.main location tree
../.venv/Scripts/python -m app.cli.main location add "A柜" --code CAB-A --parent WS --type cabinet

# 搜索
../.venv/Scripts/python -m app.cli.main search PLA
../.venv/Scripts/python -m app.cli.main search esp --json

# 属性模板
../.venv/Scripts/python -m app.cli.main attr-def list
../.venv/Scripts/python -m app.cli.main attr-def add --category-id 2 --name 颜色 --key color --type text

# 标签管理
../.venv/Scripts/python -m app.cli.main tag list

# 备份
../.venv/Scripts/python -m app.cli.main backup create
../.venv/Scripts/python -m app.cli.main backup list
../.venv/Scripts/python -m app.cli.main backup restore backup-20260514-103000
../.venv/Scripts/python -m app.cli.main backup download backup-20260514-103000 --output backup.zip
```

如果通过 `pip install -e .` 安装，可以直接使用 `stash` 命令：

```bash
stash item list
stash search PLA --json
```

---

## API 概览

所有 API 统一前缀 `/api`，统一返回格式：

```json
// 成功
{ "success": true, "data": { ... }, "message": "ok" }

// 失败
{ "success": false, "error": { "code": "ITEM_NOT_FOUND", "message": "物品不存在" } }
```

核心接口：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/items` | 物品列表（支持搜索/筛选/分页） |
| POST | `/api/items` | 新增物品 |
| GET | `/api/items/{id_or_code}` | 物品详情 |
| PATCH | `/api/items/{id_or_code}` | 修改物品 |
| DELETE | `/api/items/{id_or_code}` | 归档物品 |
| POST | `/api/items/{id}/move` | 移动位置 |
| POST | `/api/items/{id}/add` | 入库 |
| POST | `/api/items/{id}/use` | 使用/出库 |
| POST | `/api/items/{id}/adjust` | 调整数量 |
| POST | `/api/items/{id}/mark-restock` | 标记补货 |
| POST | `/api/items/{id}/favorite` | 标记常用 |
| GET | `/api/categories` `/api/categories/tree` | 分类列表/树 |
| GET | `/api/locations` `/api/locations/tree` | 位置列表/树 |
| GET | `/api/search?q=xxx` | 全局搜索 |
| GET | `/api/tags` | 标签列表 |
| POST | `/api/items/{id}/tags` | 添加标签 |
| POST | `/api/items/{id}/aliases` | 添加别名 |
| POST | `/api/items/{id}/identifiers` | 绑定外部标识 |
| POST | `/api/items/{id}/images` | 上传图片 |
| POST | `/api/items/{id}/attachments` | 上传附件 |
| GET/POST | `/api/backups` | 备份列表/创建备份 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/system/info` | 系统信息 |

---

## 项目结构

```
Maker-Stash/
├── backend/                  后端
│   ├── app/
│   │   ├── api/routes/       API 路由（items, categories, locations, search, ...）
│   │   ├── cli/              CLI 客户端（config, client, commands）
│   │   ├── core/             配置、数据库、安全、统一响应、错误处理
│   │   ├── models/           数据模型（13 个表）
│   │   ├── repositories/     数据访问层
│   │   ├── schemas/          Pydantic 请求/响应结构
│   │   ├── scripts/          初始化脚本（建库、创建 Token）
│   │   └── services/         业务逻辑层
│   ├── alembic/              数据库迁移
│   ├── tests/                测试
│   ├── pyproject.toml        Python 包配置（含 stash 命令入口）
│   └── requirements.txt      Python 依赖
├── frontend/                 前端
│   └── src/
│       ├── api/              API 封装（axios）
│       ├── components/       组件
│       │   ├── layout/       布局（AppShell, SidebarNav）
│       │   ├── panels/       面板（InventoryTable, DetailPanel, LocationMap）
│       │   ├── dialogs/      对话框（ItemForm, Quantity, Move, Tags, ...）
│       │   └── ui/           基础组件（ItemThumb, StatusDot）
│       ├── stores/           Pinia 状态管理
│       ├── views/            页面
│       ├── types/            TypeScript 类型定义
│       └── router/           Vue Router
├── prompt/start/             设计规范文档
├── start.py / stop.py        一键启停脚本
├── CLAUDE.md                 AI 开发指引
└── README.md
```

---

## 设计原则

1. **API First** — 所有核心能力先有 API，前端和 CLI 只是客户端
2. **CLI First** — 高频操作都有 CLI 命令，可自动化、可脚本化
3. **不直连数据库** — CLI 和外部模块统一走 API
4. **轻量部署** — SQLite 单文件数据库，不需要 PostgreSQL/Redis
5. **可扩展** — AI、扫码、NFC、标签打印、位置地图等模块通过 API 接入
6. **个人体验优先** — 不做工厂化库存系统，快速记录、快速查找

---

## License

MIT
