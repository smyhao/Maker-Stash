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

`create_token` 会显示一个明文 Token，只显示一次，记下来。后端数据库只保存 Token 哈希；如果忘记明文，需要重新运行脚本创建新 Token。

### 启动

```bash
# 一键启动（后端 + 前端）
python start.py
```

启动后：
- 后端 API: http://127.0.0.1:8000
- 前端页面: http://127.0.0.1:5173（自动打开浏览器）

首次使用在前端「设置 → 连接」里填入 API 地址和 Token。API 地址留空时，前端会通过当前站点的 `/api` 代理访问后端。

更多启动参数见 [START.md](START.md)。

### 关闭

```bash
python stop.py
```

---

## CLI 用法

下面以 `stash` 代替完整调用路径表示命令。未安装时用 `python -m app.cli.main` 代替 `stash`。

### 配置

```bash
stash config set api_url http://127.0.0.1:8000
stash config set token <your-token>
stash ping                                          # 测试连接
```

### 物品

```bash
stash item list                                     # 列表（支持 --json --tag --status --category --location --restock --favorite）
stash item show FIL-000001
stash item add --name "黑色 PLA" --category filament --quantity 0.42 --unit kg --tag PLA --tag 黑色
stash item add --name "ESP32" --category components --attr 型号=ESP32-S3 --attr Flash=4MB
stash item update FIL-000001 --name "黑色 PLA 耗材" --description "打印前建议烘干"
stash item delete FIL-000001                        # 归档
stash item delete FIL-000001 --force                # 归档并删除附件
stash item move FIL-000001 --to WS.DRY-A.G03
stash item add-qty FIL-000001 --amount 1 --unit kg  # 入库
stash item use FIL-000001 --amount 0.12 --unit kg   # 使用/出库
stash item adjust FIL-000001 --quantity 0.30 --unit kg
stash item restock FIL-000001
stash item unstock FIL-000001
stash item favorite FIL-000001
stash item unfavorite FIL-000001
stash item tag ELE-000001 乐鑫 开发板
stash item untag ELE-000001 乐鑫
stash item alias ELE-000001 WiFi模块
stash item unalias ELE-000001 WiFi模块
stash item notes FIL-000001
stash item add-note FIL-000001 "打印前建议烘干 4 小时"
```

### 标签、别名、外部标识

```bash
stash tag list
stash tag add PLA
stash tag delete 3
stash item bind ELE-000001 --type qrcode --value QR-ELE-000001
stash item unbind ELE-000001 5
stash item find-id QR-ELE-000001
```

### 分类

```bash
stash category list
stash category tree
stash category add "树脂材料" --slug resin --prefix RES
stash category update 3 --name "3D打印耗材"
stash category delete 7
```

### 位置

```bash
stash location list
stash location tree
stash location show WS.CAB-A                        # 按 full_code 查看
stash location show 2                               # 按 ID 查看
stash location add "A柜" --code CAB-A --parent WS --type cabinet
stash location update 2 --name "A号柜" --description "常放耗材"
stash location delete 5
stash location items WS.CAB-A                       # 查看某位置下所有物品
```

### 属性模板

```bash
stash attr-def list
stash attr-def list --category-id 2
stash attr-def add --category-id 2 --name 颜色 --key color --type text
stash attr-def update 5 --name 耗材颜色 --unit 色
stash attr-def delete 5
```

### 图片和附件

```bash
stash image-add FIL-000001 ./pla.jpg --cover
stash file-add ELE-000001 ./datasheet.pdf
stash file-list ELE-000001
stash file-delete 18
```

上传限制：

- 单个文件最大 50MB，后端通过 `max_upload_bytes` 配置控制。
- 图片接口只接受 JPEG、PNG、WebP、GIF；普通附件接口不限 MIME 类型。
- `image-add --cover` 会把该图片标记为物品封面，前端缩略图优先使用封面。

### 搜索

```bash
stash search PLA
stash search esp --category components --json
stash search 螺丝 --location WS.CAB-A
stash search 乐鑫 --tag
```

搜索覆盖 10 个维度：名称、编号、描述、分类、位置、标签、别名、备注、属性、附件名。

### 备份

```bash
stash backup create
stash backup create --note "修改分类前备份"
stash backup list
stash backup restore backup-20260514-103000
stash backup download backup-20260514-103000 --output backup.zip
```

备份恢复注意事项：

- `backup create` 默认包含上传文件；如只备份数据库，使用 `--without-uploads`。
- `backup restore` 会先创建当前状态快照，再恢复目标备份。
- 恢复会覆盖当前数据库和上传文件目录，执行前建议确认最近备份可下载。
- 同一时间只允许一个备份或恢复任务执行；冲突时稍后重试。

### 系统

```bash
stash system info
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

**物品**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/items` | 物品列表（支持 q/tag/status/category/location/need_restock/favorite 分页筛选） |
| POST | `/api/items` | 新增物品（支持 tags/attributes/note） |
| GET | `/api/items/{id_or_code}` | 物品详情 |
| PATCH | `/api/items/{id_or_code}` | 修改物品 |
| DELETE | `/api/items/{id_or_code}` | 归档物品（`?delete_attachments=true` 同时删附件） |
| POST | `/api/items/{id}/move` | 移动位置 |
| POST | `/api/items/{id}/add` | 入库 |
| POST | `/api/items/{id}/use` | 使用/出库 |
| POST | `/api/items/{id}/adjust` | 调整数量 |
| POST | `/api/items/{id}/mark-restock` | 标记补货 |
| POST | `/api/items/{id}/unmark-restock` | 取消补货 |
| POST | `/api/items/{id}/favorite` | 标记常用 |
| POST | `/api/items/{id}/unfavorite` | 取消常用 |
| GET/POST | `/api/items/{id}/notes` | 备注列表/新增备注 |
| GET/POST | `/api/items/{id}/tags` | 物品标签 |
| DELETE | `/api/items/{id}/tags/{tag}` | 移除标签 |
| GET/POST | `/api/items/{id}/aliases` | 别名列表/新增 |
| DELETE | `/api/items/{id}/aliases/{alias}` | 删除别名 |
| GET/POST | `/api/items/{id}/identifiers` | 外部标识 |
| DELETE | `/api/items/{id}/identifiers/{id}` | 解绑标识 |
| GET | `/api/items/by-identifier/{value}` | 按外部标识查找物品 |
| GET/POST | `/api/items/{id}/attributes` | 物品属性 |
| PATCH/DELETE | `/api/item-attributes/{id}` | 修改/删除属性 |

**分类**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/categories` `/api/categories/tree` | 分类列表/树 |
| POST | `/api/categories` | 新增分类 |
| PATCH/DELETE | `/api/categories/{id}` | 修改/删除分类 |
| GET | `/api/categories/{id}/attribute-definitions` | 分类下的属性模板 |

**位置**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/locations` `/api/locations/tree` | 位置列表/树 |
| POST | `/api/locations` | 新增位置 |
| GET | `/api/locations/{id}` | 位置详情 |
| GET | `/api/locations/{id}/items` | 位置下物品（按 ID） |
| GET | `/api/locations/by-code/{full_code}` | 按 full_code 查位置 |
| GET | `/api/locations/by-code/{full_code}/items` | 位置下物品（按 code） |
| PATCH/DELETE | `/api/locations/{id}` | 修改/删除位置 |

**搜索**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/search?q=xxx` | 全字段搜索（支持 category/location/tag 过滤，结果含 matched_by） |

**标签、属性模板、附件、备份、系统**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/api/tags` | 标签列表/新增 |
| DELETE | `/api/tags/{id}` | 删除标签 |
| GET/POST/PATCH/DELETE | `/api/attribute-definitions` | 属性模板 CRUD |
| POST | `/api/items/{id}/images` | 上传图片（multipart） |
| POST | `/api/items/{id}/attachments` | 上传附件（multipart） |
| GET | `/api/items/{id}/attachments` | 附件列表 |
| DELETE | `/api/attachments/{id}` | 删除附件 |
| GET | `/api/attachments/{id}/download` | 下载附件 |
| GET/POST | `/api/backups` | 备份列表/创建 |
| POST | `/api/backups/{id}/restore` | 恢复备份 |
| GET | `/api/backups/{id}/download` | 下载备份 |
| GET | `/api/stats/overview` | 统计概览 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/system/info` | 系统信息 |

---

### API 注意事项

- 所有业务 API 默认需要 `Authorization: Bearer <token>`；首次 Token 通过 `python -m app.scripts.create_token --name <name>` 创建，明文只显示一次。
- 上传限制与 CLI 一致：单文件默认 50MB，图片 MIME 仅支持 JPEG、PNG、WebP、GIF，超限返回 `UPLOAD_TOO_LARGE`。
- 恢复备份前后端会自动创建当前快照，但恢复动作仍会覆盖当前数据；生产使用前应先下载一份可离线保存的备份。

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
