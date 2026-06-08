# API 模块技术手册

## 1. 架构概览

```
请求 → FastAPI App → APIRouter(prefix="/api") → Route 函数 → Service → Database/Files
                         ↑
                   require_api_token (依赖注入)
```

所有 API 挂载在 `/api` 前缀下，由 `app/api/router.py` 统一注册，通过 `require_api_token` 依赖注入进行 Token 校验。

### 文件组织

```
app/api/
├── router.py              统一注册所有子路由
└── routes/
    ├── health.py          健康检查、系统信息、能力发现
    ├── categories.py      分类 CRUD
    ├── locations.py       位置 CRUD + 按位置查物品 + 收纳盒格位查询
    ├── items.py           物品 CRUD + 业务动作 + 备注
    ├── search.py          全局搜索
    ├── metadata.py        标签、别名、外部标识
    ├── attributes.py      属性模板 + 物品属性值
    ├── attachments.py     图片/附件上传下载
    ├── backups.py         备份创建/列表/恢复/下载
    ├── tasks.py           轻量任务 API
    ├── workflows.py       plan / confirm 工作流
    ├── tokens.py          API Token 管理
    └── stats.py           统计概览
```

### 统一响应

所有 API 通过 `app/core/response.py` 的 `ok()` 函数返回统一格式：

```python
def ok(data: Any, message: str = "ok") -> dict:
    return {"success": True, "data": data, "message": message}
```

错误通过 `AppError` / `NotFoundError` 抛出，由 `app_error_handler` 和 `validation_error_handler` 捕获：

```python
raise NotFoundError("ITEM_NOT_FOUND", "物品不存在：FIL-999999")
# → {"success": false, "error": {"code": "ITEM_NOT_FOUND", "message": "物品不存在：FIL-999999"}}
```

### 认证

`app/core/security.py` 的 `require_api_token` 作为 `APIRouter` 的全局依赖。Token 通过 `Authorization: Bearer <token>` 传递，数据库只存哈希。

首次部署没有 Token 时，使用脚本创建：

```bash
python -m app.scripts.create_token --name web
```

脚本输出的明文 Token 只显示一次；忘记后不能从数据库反查，只能重新创建并更新客户端配置。

配置项（`.env`）：
- `API_TOKEN_ENABLED` — 是否启用 Token 校验
- `API_TOKEN_REQUIRE_ALL` — 为 false 时 `/api/health` 和 `/api/system/info` 免 Token；`/api/system/capabilities` 仍按全局依赖校验，除非关闭 `API_TOKEN_ENABLED`
- `WEB_UI_TOKEN_REQUIRED` — 是否要求 Web 前端请求也携带 Token；默认 false，CLI 和外部模块仍需使用 Bearer Token

### 路由注册

在 `router.py` 中注册新路由：

```python
api_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_token)])
api_router.include_router(your_new_module.router)
```

路由文件中不需要重复写 `/api` 前缀。

---

## 2. Route 编写规范

### 分层调用

```python
@router.post("/items")
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).create(payload)
    return ok(ItemRead.model_validate(item).model_dump())
```

Route 函数只做三件事：
1. 接收参数（路径/查询/请求体）
2. 调用 Service
3. 返回 `ok(data)`

业务逻辑全部在 Service 层，Route 中不写 if/for/计算。

### 返回单个资源

```python
return ok(SchemaRead.model_validate(obj).model_dump())
```

### 返回列表

```python
data = [SchemaRead.model_validate(x).model_dump() for x in service.list()]
return ok({"items": data})
```

### 返回操作结果

```python
return ok({"deleted": True})
return ok({"archived": True, "attachments_deleted": False})
```

### 使用查询参数

```python
@router.get("")
def list_items(
    q: str | None = None,           # 可选搜索
    category: str | None = None,
    page: int = 1,                   # 带默认值
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> dict:
```

### 使用路径参数

```python
@router.get("/{id_or_code}")
def get_item(id_or_code: str, db: Session = Depends(get_db)) -> dict:
```

### 文件上传

```python
@router.post("/items/{id_or_code}/images")
async def upload_image(
    id_or_code: str,
    file: UploadFile = File(...),
    is_cover: bool = False,
    db: Session = Depends(get_db),
) -> dict:
```

上传限制：

- 单个文件默认最大 50MB，由 `settings.max_upload_bytes` 控制。
- 图片接口只允许 `image/jpeg`, `image/png`, `image/webp`, `image/gif`。
- 普通附件接口不限制 MIME 类型，但仍受单文件大小限制。
- 超过大小限制返回 `UPLOAD_TOO_LARGE`；图片 MIME 不支持返回 `UPLOAD_FAILED`。

### 文件下载

```python
@router.get("/attachments/{attachment_id}/download")
def download(attachment_id: int, db: Session = Depends(get_db)) -> FileResponse:
    attachment, path = FileService(db).get_download_path(attachment_id)
    return FileResponse(path, media_type=attachment.mime_type, filename=attachment.original_name)
```

---

## 3. Schema 规范

所有 Schema 在 `app/schemas/` 目录下，使用 Pydantic BaseModel。

### 命名约定

| 用途 | 命名 | 示例 |
|---|---|---|
| 创建请求 | `{Resource}Create` | `ItemCreate`, `TagCreate` |
| 更新请求 | `{Resource}Update` | `ItemUpdate`, `LocationUpdate` |
| 读取响应 | `{Resource}Read` | `ItemRead`, `CategoryRead` |
| 树形响应 | `{Resource}TreeNode` | `LocationTreeNode` |

### Create Schema

必填字段不用 `None`，选填字段用 `| None = None`：

```python
class ItemCreate(BaseModel):
    name: str                          # 必填
    category: str | int | None = None  # 选填
    quantity: Decimal | None = None
    status: str = "normal"             # 带默认值
```

### Update Schema

所有字段均可选，用 `exclude_unset` 实现局部更新：

```python
class ItemUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
```

### Read Schema

配置 `from_attributes=True` 以支持从 ORM 对象直接转换：

```python
class ItemRead(BaseModel):
    id: int
    code: str
    name: str
    # ...
    model_config = ConfigDict(from_attributes=True)
```

### 嵌套结构

树形节点继承 Read 并添加 `children`：

```python
class LocationTreeNode(LocationRead):
    children: list["LocationTreeNode"] = Field(default_factory=list)
```

---

## 4. 全部接口清单

### 4.1 健康检查与系统信息

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/api/system/info` | 系统信息（版本/数量/认证状态/最近备份） |
| GET | `/api/system/capabilities` | 扩展能力发现（版本/功能开关/限制/扩展契约） |
| GET | `/api/stats/overview` | 统计概览（物品/低库存/补货/分类分布/位置分布） |

统计说明：

- `category_counts` 会把子分类和孙分类物品汇总到父分类。
- `location_counts` 不展开自动格位；收纳盒内格位物品会汇总到所属收纳盒。

**GET /api/system/capabilities 响应字段：**

```json
{
  "app": "workshop-stash",
  "version": "0.1.0",
  "api_version": "0.1",
  "features": {
    "items": true,
    "categories": true,
    "locations": true,
    "attachments": true,
    "containers": true,
    "search": true,
    "backups": true,
    "tokens": true,
    "idempotency": true,
    "audit": true,
    "tasks": true,
    "workflow_plan_confirm": true,
    "extension_ui": true
  },
  "limits": {
    "max_upload_bytes": 52428800,
    "page_size_max": 100
  },
  "extension_contract": {
    "preferred_interface": "rest_api",
    "write_idempotency_required": true,
    "workflow_required_for_bulk_or_agent_writes": true
  }
}
```

Capabilities 面向扩展读取，不返回 `database_url`、`upload_dir`、`backup_dir` 等本地路径；管理诊断信息继续使用 `/api/system/info`。

### 4.2 扩展 UI (extensions)

扩展 UI 主干能力用于发现 `extensions/*/extension.json`、管理当前电脑启用状态、保存扩展本机配置，并向前端返回可渲染的 settings schema 与 action contributions。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/extensions` | 列出已发现扩展、启用状态、配置状态和声明 |
| PATCH | `/api/extensions/{extension_id}` | 启用或禁用扩展 |
| GET | `/api/extensions/{extension_id}/settings` | 获取扩展配置 schema 和当前配置 |
| PATCH | `/api/extensions/{extension_id}/settings` | 保存扩展配置 |
| GET | `/api/extensions/contributions?place=...` | 获取当前已启用扩展在指定位置的 UI 入口 |
| POST | `/api/extensions/{extension_id}/actions/{action}` | 执行扩展 action |

`extension.json` 示例：

```json
{
  "id": "label-printer",
  "name": "标签打印",
  "version": "0.1.0",
  "api_version": "0.1",
  "settings": {
    "schema": {
      "printer_name": {
        "type": "string",
        "label": "打印机名称",
        "required": true
      }
    }
  },
  "contributions": [
    {
      "place": "item.detail.actions",
      "type": "button",
      "label": "打印标签",
      "action": "print-item"
    }
  ]
}
```

当前主干支持 `string`、`number`、`boolean`、`select`、`multiselect`、`secret`、`path` 配置类型。`secret` 字段返回前端时会脱敏为 `********`。

当前 action endpoint 只完成扩展、启用状态和 action 声明校验；真实扩展执行器尚未接入时会返回 `EXTENSION_ACTION_NOT_IMPLEMENTED`。

### 4.3 物品 (items)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/items` | 物品列表（分页+筛选） |
| POST | `/api/items` | 新增物品 |
| GET | `/api/items/{id_or_code}` | 物品详情 |
| PATCH | `/api/items/{id_or_code}` | 修改物品 |
| DELETE | `/api/items/{id_or_code}` | 归档物品 |
| POST | `/api/items/{id_or_code}/move` | 移动位置 |
| POST | `/api/items/{id_or_code}/add` | 入库 |
| POST | `/api/items/{id_or_code}/use` | 使用/出库 |
| POST | `/api/items/{id_or_code}/adjust` | 调整数量 |
| POST | `/api/items/{id_or_code}/mark-restock` | 标记补货 |
| POST | `/api/items/{id_or_code}/unmark-restock` | 取消补货 |
| POST | `/api/items/{id_or_code}/favorite` | 标记常用 |
| POST | `/api/items/{id_or_code}/unfavorite` | 取消常用 |
| GET | `/api/items/{id_or_code}/notes` | 备注列表 |
| POST | `/api/items/{id_or_code}/notes` | 新增备注 |
| GET | `/api/items/by-identifier/{identifier}` | 按外部标识查找 |

**GET /api/items 查询参数：**

| 参数 | 类型 | 说明 |
|---|---|---|
| `q` | string | 全字段搜索（10 维度） |
| `category` | string | 分类 slug/名称/ID；传入父分类时包含全部子孙分类 |
| `location` | string | 位置 full_code |
| `tag` | string | 标签名（精确匹配） |
| `status` | string | 状态过滤（normal/low/empty/broken/missing/idle） |
| `need_restock` | bool | 是否需要补货 |
| `favorite` | bool | 是否常用 |
| `include_archived` | bool | 是否包含已归档（默认 false） |
| `page` | int | 页码（默认 1） |
| `page_size` | int | 每页数量（默认 20，上限 100） |

**POST /api/items 请求体 (ItemCreate)：**

```json
{
  "name": "黑色 PLA",
  "category": "filament",
  "location_code": "WS.DRY-A.G03",
  "location_text": "干燥箱 A 的 03 格",
  "quantity": "0.42",
  "unit": "kg",
  "status": "normal",
  "description": "打印前建议烘干",
  "attributes": [{"name": "颜色", "key": "color", "value": "黑色"}],
  "tags": ["PLA", "黑色"],
  "note": "测试新增"
}
```

**POST /api/items/{id_or_code}/move 请求体 (ItemMove)：**

```json
{"location_code": "WS.CAB-A.S02.G03", "location_text": "A柜第二层", "note": "整理移动", "source": "web"}
```

**POST /api/items/{id_or_code}/add 请求体 (QuantityAdd)：**

```json
{"amount": "1.0", "unit": "卷", "note": "新买一卷", "source": "cli"}
```

**POST /api/items/{id_or_code}/adjust 请求体 (QuantityAdjust)：**

```json
{"quantity": "0.42", "unit": "kg", "note": "重新称重修正", "source": "web"}
```

**POST /api/items/{id_or_code}/notes 请求体 (NoteCreate)：**

```json
{"note_type": "note", "content": "打印前建议烘干", "source": "web", "operator": "admin", "metadata_json": null}
```

**ItemRead 响应字段：**

```
id, code, name, category_id, location_id, location_text, location_display, quantity, unit,
status, description, need_restock, is_favorite, cover_attachment_id,
is_archived, created_at, updated_at
```

**写入边界：**

- `quantity` 不能为负；`add/use/adjust` 会在 Schema 和 Service 层校验。
- 已归档物品禁止库存和位置变更，包括 `move/add/use/adjust`，也包括 `PATCH /api/items/{id_or_code}` 中的 `quantity/unit/location_id/location_text` 字段。
- 关键写接口支持请求体 `request_id`，也支持请求头 `Idempotency-Key`；两者同时存在时必须一致，否则返回 `IDEMPOTENCY_KEY_MISMATCH`。
- 来源字段统一为 `source/module/operator/request_id`，关键写操作会写入审计日志。

### 4.3 分类 (categories)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/categories` | 平铺列表 |
| GET | `/api/categories/tree` | 树形结构 |
| POST | `/api/categories` | 新增分类 |
| PATCH | `/api/categories/{id}` | 修改分类 |
| DELETE | `/api/categories/{id}` | 删除分类 |

**CategoryCreate：** `name`(必填), `slug`(必填), `code_prefix`(必填), `parent_id`, `sort_order`, `description`

**CategoryUpdate：** `name`, `parent_id`, `sort_order`, `description`

**CategoryRead：** `id, name, slug, code_prefix, parent_id, sort_order, description, is_system, created_at, updated_at`

**CategoryTreeNode：** CategoryRead + `children: list[CategoryTreeNode]`

**分类树语义：**

- `parent_id` 可用于把已有分类移动到新的父分类下。
- 后端拒绝把分类移动到自身或任意子分类下，避免循环树。
- `/api/items?category=...` 和 `/api/search?category=...` 以分类分支为过滤范围；例如传入「元器件」会返回「元器件」自身以及「电阻」「电容」等子孙分类的物品。
- `/api/stats/overview` 的 `category_counts` 会把子孙分类数量汇总进父分类。

### 4.4 位置 (locations)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/locations` | 平铺列表 |
| GET | `/api/locations/tree` | 树形结构 |
| POST | `/api/locations` | 新增位置 |
| GET | `/api/locations/{id}` | 按 ID 查详情 |
| GET | `/api/locations/{id}/items` | 按 ID 查下级物品 |
| GET | `/api/locations/resolve-msloc?code=MSLOC:<full_code>` | 解析位置二维码并返回只读查看上下文 |
| GET | `/api/locations/by-code/{full_code}` | 按 full_code 查详情 |
| GET | `/api/locations/by-code/{full_code}/items` | 按 full_code 查下级物品 |
| POST | `/api/locations/containers` | 创建可视化收纳盒并生成格位 |
| POST | `/api/locations/{id}/container` | 将已有位置转换为可视化收纳盒 |
| PATCH | `/api/locations/{id}/container` | 修改收纳盒布局/外观 |
| GET | `/api/locations/{id}/board` | 获取收纳盒格位画布及占用摘要 |
| POST | `/api/locations/{id}/swap` | 在同一收纳盒内原子交换两个已占格位 |
| PATCH | `/api/locations/{id}` | 修改位置（name/type/description/sort_order） |
| DELETE | `/api/locations/{id}` | 删除位置（非空禁止删除） |

**LocationCreate：** `name`(必填), `code`(必填), `parent_code`, `type`, `description`, `sort_order`

**LocationUpdate：** `name`, `type`, `description`, `sort_order`

**LocationRead：** `id, name, code, full_code, parent_id, type, description, sort_order, layout_type, layout_rows, layout_columns, appearance_color, appearance_icon, is_slot, slot_key, slot_order, created_at, updated_at`

**注意：** `code` 和 `full_code` 创建后不可修改。

**可视化收纳盒：**

`ContainerCreate` / `ContainerUpdate` 的布局字段：

```json
{
  "name": "透明分格盒 A",
  "code": "BOX-A",
  "parent_code": "WS.CAB-A",
  "type": "box",
  "layout_type": "grid",
  "layout_rows": 3,
  "layout_columns": 5,
  "appearance_color": "#5F7F67",
  "appearance_icon": "box"
}
```

- `layout_type` 仅支持 `grid` 和 `row`。
- `appearance_color` 支持预设值 `sage/clay/sand/ink`，也支持自定义 RGB 十六进制编号 `#RRGGBB`，例如 `#5F7F67`。
- `grid` 使用 `A01...C05` 格位编号；`row` 使用 `01...N` 编号。
- 普通 `/api/locations` 和 `/api/locations/tree` 默认不返回自动格位，避免列表被叶子节点污染。
- `GET /api/locations/{id}/board` 返回 `{ container, slots }`，每个 slot 包含 `location` 和可为空的 `item`。
- 一个格位最多绑定一条未归档物品记录。向空格位放置已有物品使用物品移动接口；向已占格位移动会返回 `SLOT_OCCUPIED`。
- 缩小布局时，如果待删除格位仍有物品，返回 `CONTAINER_RESIZE_OCCUPIED`。
- 转换已有非空位置时，请求体需要 `assignments`，必须把该位置直接绑定的每条未归档物品分配到唯一格位。

**格位交换请求体：**

```json
{
  "source_item_code": "ELE-000001",
  "target_slot_key": "B03",
  "source": "web",
  "module": "locations"
}
```

交换只适用于同一收纳盒内两个已占格位，在一个事务中更新双方位置并写入记录。

**位置二维码与扫码查看协议：**

首版二维码内容使用短协议：

```text
MSLOC:<location.full_code>
```

示例：

```text
MSLOC:WS.BOX-A.A03
```

协议语义：

- `MSLOC:` 是位置二维码协议标识。
- 后缀必须是现有 `locations.full_code`。
- 二维码绑定容器或格位位置，不绑定物品，不使用 `identifiers` 表。
- 标签上不打印物品名称、数量或库存状态；这些信息必须扫码后通过 API 查询当前状态。
- `code/full_code` 创建后不可修改，是保持已打印标签长期有效的前提。

推荐扫码查看直接调用：

```http
GET /api/locations/resolve-msloc?code=MSLOC:WS.BOX-A.A03
```

响应按 `kind` 区分：

- `kind=slot`：返回 `location`、所属 `container`、当前 `slot`；`slot.item` 可为空。
- `kind=container`：返回 `container` 和 `slots`，每个 `slot.item` 可为空。
- `kind=location`：返回普通 `location` 和 `items`。

示例响应：

```json
{
  "kind": "slot",
  "full_code": "WS.BOX-A.A03",
  "location": {"full_code": "WS.BOX-A.A03", "is_slot": true},
  "container": {"full_code": "WS.BOX-A"},
  "slot": {
    "location": {"slot_key": "A03"},
    "item": null
  }
}
```

底层解析流程：

1. 客户端校验内容以 `MSLOC:` 开头，取后缀 `full_code`。
2. 调用 `GET /api/locations/by-code/{full_code}` 查询位置。
3. 如果 `is_slot=true`，用返回的 `parent_id` 调用 `GET /api/locations/{parent_id}/board`，在 `slots` 中匹配该格位，读取可为空的 `item`。
4. 如果 `layout_type` 非空且 `is_slot=false`，调用 `GET /api/locations/{id}/board` 展示容器格位布局。
5. 如果是普通位置，调用 `GET /api/locations/{id}/items` 展示当前位置物品。

格位扫码结果应保持只读。移动、放入、取出、交换等写操作仍使用既有物品移动和格位交换接口，不属于扫码查看首版流程。

### 4.5 搜索 (search)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/search` | 全字段搜索 |

**查询参数：** `q`(必填), `category`, `location`, `tag`, `limit`(默认20), `include_archived`(默认false)

`category` 与物品列表一致，按分类分支过滤；传入父分类时包含所有子孙分类。

**搜索结果字段：**

```
id, code, name, category_id, category_name, location_id, location_full_code,
quantity, unit, status, cover_attachment_id, need_restock, is_favorite, matched_by
```

`matched_by` 可能值：`name`, `code`, `description`, `alias`, `tag`, `attribute`, `note`, `attachment`, `category`, `location`

搜索逻辑在 `services/search_service.py` 的 `fulltext_where()` 函数，`/api/items?q=` 和 `/api/search` 共用。

前端全局搜索建议使用 `/api/items?q=<keyword>&page=1&page_size=6` 获取候选物品，点击候选后切到库存页并选中对应物品。该交互不需要额外 API。

### 4.6 标签 (tags)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tags` | 标签列表 |
| POST | `/api/tags` | 新增标签 |
| DELETE | `/api/tags/{id}` | 删除标签（同时清除物品关联） |
| GET | `/api/items/{id_or_code}/tags` | 物品标签列表 |
| POST | `/api/items/{id_or_code}/tags` | 给物品添加标签 |
| DELETE | `/api/items/{id_or_code}/tags/{tag}` | 移除物品标签 |

**TagCreate：** `name`(必填), `slug`

**ItemTagsUpdate：** `tags: list[str]`(必填)

### 4.7 别名 (aliases)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/items/{id_or_code}/aliases` | 别名列表 |
| POST | `/api/items/{id_or_code}/aliases` | 新增别名 |
| DELETE | `/api/items/{id_or_code}/aliases/{alias}` | 删除别名 |

**AliasCreate：** `alias`(必填)

### 4.8 外部标识 (identifiers)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/items/{id_or_code}/identifiers` | 绑定外部标识 |
| DELETE | `/api/items/{id_or_code}/identifiers/{identifier_id}` | 解绑 |

**IdentifierCreate：** `type`(必填), `value`(必填), `description`

标识类型建议：`qrcode`, `nfc`, `barcode`, `custom`, `external`

### 4.9 属性 (attributes)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/attribute-definitions` | 属性模板列表（可按 category_id 过滤） |
| GET | `/api/categories/{id}/attribute-definitions` | 某分类下的属性模板 |
| POST | `/api/attribute-definitions` | 新增属性模板 |
| PATCH | `/api/attribute-definitions/{id}` | 修改属性模板 |
| DELETE | `/api/attribute-definitions/{id}` | 删除属性模板 |
| GET | `/api/items/{id_or_code}/attributes` | 物品属性列表 |
| POST | `/api/items/{id_or_code}/attributes` | 新增物品属性 |
| PATCH | `/api/item-attributes/{id}` | 修改物品属性 |
| DELETE | `/api/item-attributes/{id}` | 删除物品属性 |

**AttributeDefinitionCreate：** `category_id`(必填), `name`(必填), `key`(必填), `field_type`(默认text), `unit`, `options_json`, `required`(默认false), `sort_order`

**ItemAttributeValueCreate：** `name`(必填), `key`(必填), `value`, `value_type`(默认text), `unit`, `attribute_definition_id`, `sort_order`

### 4.10 附件 (attachments)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/items/{id_or_code}/images` | 上传图片（multipart，`is_cover` 查询参数） |
| POST | `/api/items/{id_or_code}/attachments` | 上传附件（multipart） |
| GET | `/api/items/{id_or_code}/attachments` | 附件列表 |
| DELETE | `/api/attachments/{id}` | 删除附件并释放上传文件 |
| GET | `/api/attachments/{id}/download` | 下载附件 |
| GET | `/api/attachments/{id}/thumbnail` | 下载图片缩略图（JPEG） |

**AttachmentRead：** `id, item_id, attachment_type, original_name, stored_name, file_path, thumbnail_path, mime_type, size_bytes, description, is_cover, is_deleted, created_at`

上传约束：单文件默认 50MB；图片只支持 JPEG/PNG/WebP/GIF；`/api/items/{id_or_code}/images?is_cover=true` 会把上传图片设置为物品封面。

前端展示约定：

- 物品详情封面和列表缩略图优先使用 `cover_attachment_id` 指向的图片。
- 附件区面向手册、数据表、说明文档等资料，只隐藏当前封面资产，避免重复显示封面图。
- 通过普通附件入口上传的图片仍属于资料附件，应继续在附件列表展示。

删除语义：

- `DELETE /api/attachments/{id}` 会标记附件删除，并同步删除上传原文件和缩略图文件。
- 如果删除的是当前封面，会同步清空物品 `cover_attachment_id`，避免前端继续请求已删除缩略图。
- `DELETE /api/items/{id_or_code}?delete_attachments=true` 会归档物品，并释放该物品所有附件原文件和缩略图。
- 普通归档不删除附件文件，只隐藏归档物品；需要释放磁盘空间时必须传 `delete_attachments=true`。

### 4.11 API Token (tokens)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tokens` | Token 列表 |
| POST | `/api/tokens` | 创建 Token，明文 token 只在本次响应返回 |
| PATCH | `/api/tokens/{id}` | 修改 Token 名称、启用状态或描述 |
| DELETE | `/api/tokens/{id}` | 删除 Token |

**TokenCreate：** `name`(必填), `description`

**TokenUpdate：** `name`, `enabled`, `description`

**TokenRead：** `id, name, enabled, description, last_used_at, created_at, updated_at, is_current`

**TokenCreated：** TokenRead + `token`

注意事项：

- 数据库只保存 token 哈希，不保存明文。
- `POST /api/tokens` 返回的 `token` 明文只出现一次，客户端必须立即保存。
- `GET /api/tokens` 支持查询参数 `current_token`；传入明文 token 时会在匹配项上标记 `is_current=true`。
- 禁用 token 使用 `PATCH /api/tokens/{id}`，请求体 `{"enabled": false}`。

### 4.12 备份 (backups)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/backups` | 创建备份 |
| GET | `/api/backups` | 备份列表 |
| POST | `/api/backups/{backup_id}/restore` | 恢复备份（恢复前自动快照） |
| GET | `/api/backups/{backup_id}/download` | 下载备份文件 |

**BackupCreate：** `include_uploads`(默认true), `note`

**BackupRead：** `id, backup_id, file_path, size_bytes, include_uploads, note, status, created_at`

恢复注意事项：

- `include_uploads=false` 只备份数据库，不包含 `uploads` 目录。
- 恢复前会自动创建当前状态快照。
- 恢复会覆盖当前数据库和上传文件目录；外部部署应先确认目标备份文件已下载或可重新获取。
- 同一时间只允许一个备份或恢复任务执行，冲突返回 `BACKUP_IN_PROGRESS`。

### 4.13 任务 (tasks)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/tasks` | 提交轻量任务 |
| GET | `/api/tasks/{task_id}` | 查询任务详情 |
| GET | `/api/tasks/{task_id}/status` | 查询任务状态 |

**TaskCreate：** `job_type`(必填), `input_summary`, `source`, `module`, `operator`, `request_id`

任务状态固定为：`queued`, `running`, `succeeded`, `failed`。

任务提交支持 `request_id` / `Idempotency-Key` 幂等；同一键重复提交返回同一个任务。

失败任务状态响应包含稳定错误结构：

```json
{
  "task": {
    "task_id": "task-...",
    "status": "failed",
    "job_type": "batch_import",
    "error": {"code": "TASK_FAILED", "message": "CSV 缺少必填列 name"}
  }
}
```

### 4.14 工作流 (workflows)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/workflows/plans` | 创建 plan / dry-run |
| GET | `/api/workflows/plans/{plan_id}` | 查询 plan 和 confirm 结果 |
| POST | `/api/workflows/plans/{plan_id}/confirm` | 基于 plan 确认执行 |

当前支持的 `workflow_type`：

- `batch_import`：批量导入预演和确认执行。
- `batch_outbound`：批量出库预演和确认执行。
- `agent_operation`：Agent 操作计划输出；当前只生成计划，不执行外部副作用。

plan 响应包含：

```
plan_id, workflow_type, status, summary, creates, updates, skips,
failures, risks, confirm_token, task_id, source, module, operator,
request_id, created_at, confirmed_at
```

confirm 规则：

- 必须传入 plan 返回的 `confirm_token`。
- plan 存在 `failures` 时不能 confirm，返回 `PLAN_HAS_FAILURES`。
- confirm 不重新自由计算输入，只执行已保存的 plan 结果。
- confirm 会创建并更新任务记录；成功时任务为 `succeeded`，失败时任务为 `failed`。
- confirm 中的业务写入、plan 确认状态和任务成功状态在同一事务内完成；若业务执行中途失败，会回滚已执行的业务写入，并保留 failed task 供排查。
- 重复 confirm 已确认的 plan 不会重复执行副作用。

---

## 5. 错误码

| 错误码 | HTTP 状态 | 说明 |
|---|---|---|
| `ITEM_NOT_FOUND` | 404 | 物品不存在 |
| `CATEGORY_NOT_FOUND` | 404 | 分类不存在 |
| `LOCATION_NOT_FOUND` | 404 | 位置不存在 |
| `TAG_NOT_FOUND` | 404 | 标签不存在 |
| `TOKEN_NOT_FOUND` | 404 | Token 不存在 |
| `ATTACHMENT_NOT_FOUND` | 404 | 附件不存在 |
| `THUMBNAIL_NOT_FOUND` | 404 | 缩略图不存在 |
| `BACKUP_NOT_FOUND` | 404 | 备份不存在 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `PLAN_NOT_FOUND` | 404 | 工作流计划不存在 |
| `BACKUP_IN_PROGRESS` | 409 | 已有备份或恢复任务正在执行 |
| `INVALID_TOKEN` | 401 | Token 无效或缺失 |
| `DUPLICATE_CODE` | 400 | 编号重复 |
| `LOCATION_CODE_EXISTS` | 400 | 位置编号已存在 |
| `INVALID_MSLOC_CODE` | 400 | 位置二维码协议无效 |
| `LOCATION_NOT_EMPTY` | 400 | 位置非空，不能删除 |
| `LOCATION_NOT_CONTAINER` | 400 | 位置不是可视化收纳盒 |
| `LOCATION_HAS_CHILDREN` | 400 | 位置已有子位置，不能转换为收纳盒 |
| `LOCATION_ALREADY_CONTAINER` | 400 | 位置已经是可视化收纳盒 |
| `CONTAINER_ASSIGNMENTS_REQUIRED` | 400 | 转换非空位置为收纳盒时缺少格位分配 |
| `CONTAINER_RESIZE_OCCUPIED` | 400 | 缩小收纳盒布局会删除已占格位 |
| `CONTAINER_CHILD_FORBIDDEN` | 400 | 收纳盒或格位下禁止创建普通子位置 |
| `SLOT_OCCUPIED` | 400 | 目标格位已占用 |
| `SLOT_NOT_FOUND` | 404 | 格位不存在 |
| `SOURCE_NOT_IN_CONTAINER` | 400 | 交换源物品不在当前收纳盒内 |
| `TARGET_SLOT_EMPTY` | 400 | 交换目标格位为空 |
| `SAME_SLOT` | 400 | 不能交换同一格位 |
| `NEGATIVE_QUANTITY_NOT_ALLOWED` | 400 | 库存不能变为负数 |
| `ARCHIVED_ITEM_QUANTITY_FORBIDDEN` | 400 | 已归档物品不能变更库存 |
| `ARCHIVED_ITEM_MOVE_FORBIDDEN` | 400 | 已归档物品不能移动位置 |
| `IDEMPOTENCY_KEY_MISMATCH` | 400 | 请求体 request_id 与 Idempotency-Key 不一致 |
| `IDEMPOTENCY_KEY_CONFLICT` | 409 | 幂等键已被其他写操作使用 |
| `PLAN_CONFIRM_TOKEN_INVALID` | 409 | plan 确认标识不匹配 |
| `PLAN_HAS_FAILURES` | 409 | plan 含失败项，不能确认执行 |
| `INVALID_TASK_STATE` | 409 | 任务状态迁移非法 |
| `UNSUPPORTED_WORKFLOW_TYPE` | 400 | 不支持的工作流类型 |
| `VALIDATION_ERROR` | 422 | 参数校验失败 |
| `UPLOAD_FAILED` | 400 | 上传失败 |
| `UPLOAD_TOO_LARGE` | 413 | 上传文件超过大小限制 |

---

## 6. 新增接口 Checklist

新增 API 时按以下顺序：

1. **Model** — 如果需要新表，在 `app/models/` 添加，运行 `alembic revision --autogenerate`
2. **Schema** — 在 `app/schemas/` 添加 Create/Update/Read
3. **Service** — 在 `app/services/` 添加业务逻辑
4. **Route** — 在 `app/api/routes/` 添加路由函数
5. **Router** — 在 `app/api/router.py` 注册
6. **Test** — 在 `tests/` 添加测试
7. **Doc** — 更新本手册、`backend/README.md`，以及必要时的 `docs/extensions/` 文档
8. **Capabilities** — 新增扩展可见能力或限制时，更新 `/api/system/capabilities`

如果新增接口会被扩展长期依赖，必须同时确认：

- 是否需要稳定错误码，并写入本手册和 `docs/extensions/API.md`。
- 是否需要幂等和 `source/module/operator/request_id`。
- 是否属于批量或 Agent 写入；如是，优先设计为 workflow。
