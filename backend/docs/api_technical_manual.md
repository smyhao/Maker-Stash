# API 模块技术手册

## 1. 架构概览

```
请求 → FastAPI App → APIRouter(prefix="/api") → Route 函数 → Service → Repository → Database/Files
                         ↑
                   require_api_token (依赖注入)
```

所有 API 挂载在 `/api` 前缀下，由 `app/api/router.py` 统一注册，通过 `require_api_token` 依赖注入进行 Token 校验。

### 文件组织

```
app/api/
├── router.py              统一注册所有子路由
└── routes/
    ├── health.py          健康检查、系统信息
    ├── categories.py      分类 CRUD
    ├── locations.py       位置 CRUD + 按位置查物品
    ├── items.py           物品 CRUD + 业务动作 + 备注
    ├── search.py          全局搜索
    ├── metadata.py        标签、别名、外部标识
    ├── attributes.py      属性模板 + 物品属性值
    ├── attachments.py     图片/附件上传下载
    ├── backups.py         备份创建/列表/恢复/下载
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

配置项（`.env`）：
- `API_TOKEN_ENABLED` — 是否启用 Token 校验
- `API_TOKEN_REQUIRE_ALL` — 为 false 时 `/api/health` 和 `/api/system/info` 免 Token

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
| GET | `/api/stats/overview` | 统计概览（物品/低库存/补货/分类分布/位置分布） |

### 4.2 物品 (items)

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
| `category` | string | 分类 slug/名称/ID |
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
id, code, name, category_id, location_id, location_text, quantity, unit,
status, description, need_restock, is_favorite, cover_attachment_id,
is_archived, created_at, updated_at
```

### 4.3 分类 (categories)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/categories` | 平铺列表 |
| GET | `/api/categories/tree` | 树形结构 |
| POST | `/api/categories` | 新增分类 |
| PATCH | `/api/categories/{id}` | 修改分类 |
| DELETE | `/api/categories/{id}` | 删除分类 |

**CategoryCreate：** `name`(必填), `slug`(必填), `code_prefix`(必填), `parent_id`, `sort_order`, `description`

**CategoryUpdate：** `name`, `sort_order`, `description`

**CategoryRead：** `id, name, slug, code_prefix, parent_id, sort_order, description, is_system, created_at, updated_at`

**CategoryTreeNode：** CategoryRead + `children: list[CategoryTreeNode]`

### 4.4 位置 (locations)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/locations` | 平铺列表 |
| GET | `/api/locations/tree` | 树形结构 |
| POST | `/api/locations` | 新增位置 |
| GET | `/api/locations/{id}` | 按 ID 查详情 |
| GET | `/api/locations/{id}/items` | 按 ID 查下级物品 |
| GET | `/api/locations/by-code/{full_code}` | 按 full_code 查详情 |
| GET | `/api/locations/by-code/{full_code}/items` | 按 full_code 查下级物品 |
| PATCH | `/api/locations/{id}` | 修改位置（name/type/description/sort_order） |
| DELETE | `/api/locations/{id}` | 删除位置（非空禁止删除） |

**LocationCreate：** `name`(必填), `code`(必填), `parent_code`, `type`, `description`, `sort_order`

**LocationUpdate：** `name`, `type`, `description`, `sort_order`

**LocationRead：** `id, name, code, full_code, parent_id, type, description, sort_order, created_at, updated_at`

**注意：** `code` 和 `full_code` 创建后不可修改。

### 4.5 搜索 (search)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/search` | 全字段搜索 |

**查询参数：** `q`(必填), `category`, `location`, `tag`, `limit`(默认20), `include_archived`(默认false)

**搜索结果字段：**

```
id, code, name, category_id, category_name, location_id, location_full_code,
quantity, unit, status, cover_attachment_id, need_restock, is_favorite, matched_by
```

`matched_by` 可能值：`name`, `code`, `description`, `alias`, `tag`, `attribute`, `note`, `attachment`, `category`, `location`

搜索逻辑在 `services/search_service.py` 的 `fulltext_where()` 函数，`/api/items?q=` 和 `/api/search` 共用。

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
| POST | `/api/items/{id_or_code}/images` | 上传图片（multipart，`is_cover` 表单字段） |
| POST | `/api/items/{id_or_code}/attachments` | 上传附件（multipart） |
| GET | `/api/items/{id_or_code}/attachments` | 附件列表 |
| DELETE | `/api/attachments/{id}` | 软删除附件 |
| GET | `/api/attachments/{id}/download` | 下载附件 |

**AttachmentRead：** `id, item_id, attachment_type, original_name, stored_name, file_path, mime_type, size_bytes, description, is_cover, is_deleted, created_at`

### 4.11 备份 (backups)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/backups` | 创建备份 |
| GET | `/api/backups` | 备份列表 |
| POST | `/api/backups/{backup_id}/restore` | 恢复备份（恢复前自动快照） |
| GET | `/api/backups/{backup_id}/download` | 下载备份文件 |

**BackupCreate：** `include_uploads`(默认true), `note`

**BackupRead：** `id, backup_id, file_path, size_bytes, include_uploads, note, status, created_at`

---

## 5. 错误码

| 错误码 | HTTP 状态 | 说明 |
|---|---|---|
| `ITEM_NOT_FOUND` | 404 | 物品不存在 |
| `CATEGORY_NOT_FOUND` | 404 | 分类不存在 |
| `LOCATION_NOT_FOUND` | 404 | 位置不存在 |
| `TAG_NOT_FOUND` | 404 | 标签不存在 |
| `BACKUP_NOT_FOUND` | 404 | 备份不存在 |
| `INVALID_TOKEN` | 401 | Token 无效或缺失 |
| `DUPLICATE_CODE` | 400 | 编号重复 |
| `LOCATION_CODE_EXISTS` | 400 | 位置编号已存在 |
| `LOCATION_NOT_EMPTY` | 400 | 位置非空，不能删除 |
| `VALIDATION_ERROR` | 422 | 参数校验失败 |
| `UPLOAD_FAILED` | 400 | 上传失败 |

---

## 6. 新增接口 Checklist

新增 API 时按以下顺序：

1. **Model** — 如果需要新表，在 `app/models/` 添加，运行 `alembic revision --autogenerate`
2. **Schema** — 在 `app/schemas/` 添加 Create/Update/Read
3. **Service** — 在 `app/services/` 添加业务逻辑
4. **Route** — 在 `app/api/routes/` 添加路由函数
5. **Router** — 在 `app/api/router.py` 注册
6. **Test** — 在 `tests/` 添加测试
7. **Doc** — 更新本手册和 `backend/README.md`
