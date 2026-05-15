# 工坊物栈 MVP 数据模型设计与开发 Prompt

## 1. 文档目的

本文档用于定义“工坊物栈”第一版 MVP 的后端数据模型、表结构、字段含义、关系约束、索引建议，以及后续开发后端和前端时可直接使用的 Prompt。

系统定位为：

> 面向个人工坊的轻量化资源管理框架，用于管理元器件、3D 打印耗材、工具、备用材料、线材及其他工坊物品。

系统不追求工厂化、ERP 化或严格仓储流程，而是强调：

```text
快速记录
快速查找
灵活修改
位置清楚
照片和附件完整
API / CLI 可调用
后续模块可扩展
```

---

# 第一部分：MVP 数据模型设计

## 2. 数据模型总览

第一版 MVP 建议包含以下核心数据表：

```text
items                    物品主表
categories               分类表
locations                位置表
attribute_definitions    分类字段模板表
item_attribute_values    物品自定义属性值表
tags                     标签表
item_tags                物品标签关联表
aliases                  物品别名表
notes                    备注 / 操作记录表
attachments              图片与附件表
identifiers              外部标识绑定表
api_tokens               API Token 表
backups                  备份记录表
system_settings          系统配置表
```

核心关系：

```text
Category 1 ─── N Item
Location 1 ─── N Item
Item 1 ─── N ItemAttributeValue
Category 1 ─── N AttributeDefinition
Item N ─── N Tag
Item 1 ─── N Alias
Item 1 ─── N Note
Item 1 ─── N Attachment
Item 1 ─── N Identifier
```

---

## 3. 设计原则

### 3.1 通用主表 + 自定义属性

不要为元器件、3D 打印耗材、工具、线材分别建立完全独立的主表。第一版采用：

```text
items 通用主表
+
attribute_definitions 分类字段模板
+
item_attribute_values 具体字段值
```

这样可以支持未来新增材料类型，不需要频繁改数据库结构。

### 3.2 中文用于显示，稳定编码不用中文

中文名称可以自由使用，例如：

```text
元器件
3D打印耗材
黑色 PLA
A柜第二层
```

但稳定编号、slug、code、full_code 应尽量只使用：

```text
A-Z
0-9
-
_
.
```

避免 URL、CLI、二维码、外部模块、文件路径等场景出现编码问题。

### 3.3 位置系统只管理逻辑位置

核心系统只负责：

```text
层级位置
统一位置编号
位置下物品查询
位置树接口
```

不负责机械臂坐标、抓取点、运动规划、实际物理标定等数据。这些由后续独立模块通过 `location.full_code` 关联管理。

### 3.4 CLI 和外部模块不直连数据库

CLI、AI、扫码、NFC、标签打印、位置地图等模块必须统一通过 API 调用系统能力。

---

# 4. 表结构设计

## 4.1 `categories` 分类表

### 作用

用于管理一级分类、二级分类和用户自定义分类。

默认一级分类建议：

```text
元器件
3D打印耗材
工具
备用材料
线材
其他
```

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `name` | string | 是 | 显示名称，例如“元器件” |
| `slug` | string | 是 | 稳定标识，例如 `components` |
| `code_prefix` | string | 是 | 物品编号前缀，例如 `ELE` |
| `parent_id` | integer/null | 否 | 上级分类 ID |
| `sort_order` | integer | 否 | 排序 |
| `description` | text/null | 否 | 分类说明 |
| `is_system` | boolean | 是 | 是否系统默认分类 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

### 约束

```text
slug 唯一
同一 parent_id 下 name 不重复
code_prefix 建议唯一，但可根据实际需要放宽
```

### 示例

```text
name = 元器件
slug = components
code_prefix = ELE
```

```text
name = 3D打印耗材
slug = filament
code_prefix = FIL
```

---

## 4.2 `locations` 位置表

### 作用

用于管理逻辑存放位置和统一层级编号。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `name` | string | 是 | 显示名称，例如“03格” |
| `code` | string | 是 | 当前层级编号，例如 `G03` |
| `full_code` | string | 是 | 完整层级编号，例如 `WS.CAB-A.S02.G03` |
| `parent_id` | integer/null | 否 | 上级位置 ID |
| `type` | string | 否 | 位置类型 |
| `description` | text/null | 否 | 说明 |
| `sort_order` | integer | 否 | 排序 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

### 位置类型建议

```text
room        房间 / 工坊
cabinet     柜子
shelf       层 / 架
drawer      抽屉
box         盒子
grid        格子
wall        墙面
desk        桌面
drybox      干燥箱
custom      自定义
```

### 编号规则

```text
每一级位置都有自己的 code
full_code = 父级 full_code + . + 当前 code
根位置 full_code = code
同一父级下 code 唯一
full_code 全局唯一
```

### 示例

| name | code | full_code |
|---|---|---|
| 工坊 | `WS` | `WS` |
| A柜 | `CAB-A` | `WS.CAB-A` |
| 第二层 | `S02` | `WS.CAB-A.S02` |
| 03格 | `G03` | `WS.CAB-A.S02.G03` |

### 重要说明

位置表不保存机械臂坐标、地图坐标、抓取策略等数据。外部模块应通过 `full_code` 自行绑定扩展数据。

---

## 4.3 `items` 物品主表

### 作用

保存所有物品的通用信息。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `code` | string | 是 | 稳定物品编号，例如 `FIL-000001` |
| `name` | string | 是 | 物品名称 |
| `category_id` | integer/null | 否 | 分类 ID |
| `location_id` | integer/null | 否 | 结构化位置 ID |
| `location_text` | string/null | 否 | 自由位置文本 |
| `quantity` | decimal/null | 否 | 数量 / 剩余量 |
| `unit` | string/null | 否 | 单位，例如 `个`、`kg`、`m`、`卷` |
| `status` | string | 是 | 状态 |
| `description` | text/null | 否 | 备注 |
| `need_restock` | boolean | 是 | 是否需要补货 |
| `is_favorite` | boolean | 是 | 是否常用 |
| `cover_attachment_id` | integer/null | 否 | 封面图片附件 ID |
| `is_archived` | boolean | 是 | 是否归档 / 软删除 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

### 状态建议

第一版状态保持轻量：

```text
normal       正常
low          少量
empty        已用完
broken       损坏
missing      找不到
idle         闲置
archived     已归档
```

### 约束

```text
code 全局唯一
quantity 允许为空
category_id 可为空，但建议新建物品时尽量选择分类
location_id 和 location_text 可同时存在，也可只填一个
```

### 编号示例

```text
ELE-000001      元器件
FIL-000001      3D打印耗材
TOOL-000001     工具
MAT-000001      备用材料
CAB-000001      线材
OTH-000001      其他
```

---

## 4.4 `attribute_definitions` 分类字段模板表

### 作用

定义某个分类下常用的字段模板。

例如 3D 打印耗材常用字段：

```text
材料类型
颜色
线径
净重
剩余质量
推荐喷嘴温度
推荐热床温度
是否开封
是否受潮
```

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `category_id` | integer | 是 | 所属分类 ID |
| `name` | string | 是 | 显示字段名，例如“颜色” |
| `key` | string | 是 | 字段标识，例如 `color` |
| `field_type` | string | 是 | 字段类型 |
| `unit` | string/null | 否 | 默认单位 |
| `options_json` | text/null | 否 | select 类型选项，JSON 字符串 |
| `required` | boolean | 是 | 是否必填，个人系统默认 false |
| `sort_order` | integer | 否 | 排序 |
| `is_enabled` | boolean | 是 | 是否启用 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

### 字段类型建议

```text
text        文本
number      数字
select      单选
multi       多选
date        日期
url         链接
boolean     布尔值
textarea    长文本
```

### 约束

```text
同一 category_id 下 key 唯一
field_type 必须在允许范围内
```

---

## 4.5 `item_attribute_values` 物品属性值表

### 作用

保存具体物品的扩展字段值。

它既支持来源于分类模板的字段，也支持临时自定义字段。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `item_id` | integer | 是 | 所属物品 ID |
| `attribute_definition_id` | integer/null | 否 | 对应字段模板，可为空 |
| `name` | string | 是 | 显示字段名 |
| `key` | string | 是 | 字段标识 |
| `value` | text/null | 否 | 字段值，统一以文本保存 |
| `value_type` | string | 否 | 字段类型 |
| `unit` | string/null | 否 | 单位 |
| `sort_order` | integer | 否 | 排序 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

### 示例

黑色 PLA：

```text
材料 = PLA
颜色 = 黑色
线径 = 1.75 mm
剩余质量 = 0.42 kg
```

ESP32-S3 模块：

```text
型号 = ESP32-S3
Flash = 4MB
通信 = Wi-Fi + BLE
封装 = 模块
```

---

## 4.6 `tags` 标签表

### 作用

用于增强筛选和搜索。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `name` | string | 是 | 标签名 |
| `slug` | string/null | 否 | 稳定标识 |
| `created_at` | datetime | 是 | 创建时间 |

### 约束

```text
name 唯一
```

---

## 4.7 `item_tags` 物品标签关联表

### 作用

实现物品和标签的多对多关系。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `item_id` | integer | 是 | 物品 ID |
| `tag_id` | integer | 是 | 标签 ID |

### 约束

```text
(item_id, tag_id) 唯一
```

---

## 4.8 `aliases` 物品别名表

### 作用

增强搜索体验，支持用户用不完整、不标准、习惯性称呼搜索。

例如：

```text
ESP32-S3 模块
别名：开发板、乐鑫、WiFi模块
```

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `item_id` | integer | 是 | 物品 ID |
| `alias` | string | 是 | 别名 |
| `created_at` | datetime | 是 | 创建时间 |

### 约束

```text
同一 item_id 下 alias 不重复
```

---

## 4.9 `notes` 备注 / 操作记录表

### 作用

保存轻量备注和业务动作记录。

系统不做严格库存流水，但需要保留个人使用记录。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `item_id` | integer/null | 否 | 关联物品，可为空 |
| `note_type` | string | 是 | 记录类型 |
| `content` | text | 是 | 记录内容 |
| `quantity_change` | decimal/null | 否 | 数量变化 |
| `quantity_after` | decimal/null | 否 | 变化后数量 |
| `source` | string | 是 | 来源 |
| `operator` | string/null | 否 | 操作者 |
| `metadata_json` | text/null | 否 | 附加信息 JSON |
| `created_at` | datetime | 是 | 创建时间 |

### note_type 建议

```text
note        普通备注
add         增加数量
use         使用 / 消耗
adjust      调整数量
move        移动位置
restock     补货标记
status      状态变化
system      系统记录
```

### source 建议

```text
web
cli
api
ai
scanner
nfc
label_printer
system
```

---

## 4.10 `attachments` 图片与附件表

### 作用

保存图片、Datasheet、说明书、发票、购买截图、其他文件的元信息。

实际文件不存入数据库，只存放在本地文件目录。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `item_id` | integer | 是 | 所属物品 ID |
| `attachment_type` | string | 是 | 类型 |
| `original_name` | string | 是 | 原始文件名 |
| `stored_name` | string | 是 | 存储文件名 |
| `file_path` | string | 是 | 相对路径 |
| `mime_type` | string/null | 否 | MIME 类型 |
| `size_bytes` | integer/null | 否 | 文件大小 |
| `description` | text/null | 否 | 文件说明 |
| `is_cover` | boolean | 是 | 是否封面图 |
| `created_at` | datetime | 是 | 上传时间 |

### attachment_type 建议

```text
image       图片
manual      说明书
datasheet   数据手册
invoice     发票 / 购买凭证
link_file   链接截图 / 页面保存
other       其他
```

### 文件目录建议

```text
data/
├── uploads/
│   ├── images/
│   ├── attachments/
│   └── thumbnails/
└── backups/
```

---

## 4.11 `identifiers` 外部标识表

### 作用

用于绑定二维码、NFC、条形码、外部系统 ID 等。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `item_id` | integer | 是 | 物品 ID |
| `type` | string | 是 | 标识类型 |
| `value` | string | 是 | 标识值 |
| `description` | text/null | 否 | 说明 |
| `created_at` | datetime | 是 | 创建时间 |

### type 建议

```text
qrcode
nfc
barcode
custom
external
```

### 约束

```text
(type, value) 全局唯一
```

---

## 4.12 `api_tokens` API Token 表

### 作用

用于 CLI 和外部模块访问 API。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `name` | string | 是 | Token 名称，例如 CLI、AI助手 |
| `token_hash` | string | 是 | Token 哈希值 |
| `enabled` | boolean | 是 | 是否启用 |
| `description` | text/null | 否 | 说明 |
| `last_used_at` | datetime/null | 否 | 最近使用时间 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

### 说明

数据库中不应存储明文 Token，只保存哈希。

---

## 4.13 `backups` 备份记录表

### 作用

记录每次备份的元信息。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `backup_id` | string | 是 | 备份编号 |
| `file_path` | string | 是 | 备份文件路径 |
| `size_bytes` | integer/null | 否 | 文件大小 |
| `include_uploads` | boolean | 是 | 是否包含上传文件 |
| `note` | text/null | 否 | 备份备注 |
| `status` | string | 是 | 状态 |
| `created_at` | datetime | 是 | 创建时间 |

### status 建议

```text
success
failed
restored
```

---

## 4.14 `system_settings` 系统配置表

### 作用

保存部分运行配置。注意敏感配置仍应优先通过环境变量管理。

### 字段设计

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | integer | 是 | 主键 |
| `key` | string | 是 | 配置键 |
| `value` | text/null | 否 | 配置值 |
| `value_type` | string | 是 | 类型 |
| `description` | text/null | 否 | 说明 |
| `updated_at` | datetime | 是 | 更新时间 |

### 示例

```text
default_page_size = 20
backup_keep_days = 30
```

认证相关建议仍使用环境变量：

```env
AUTH_LOGIN_ENABLED=false
API_TOKEN_ENABLED=true
API_TOKEN_REQUIRE_ALL=true
```

---

# 5. 索引建议

## 5.1 必要索引

```text
items.code
items.name
items.category_id
items.location_id
items.need_restock
items.is_favorite
items.is_archived
categories.slug
categories.parent_id
locations.full_code
locations.parent_id
tags.name
aliases.alias
identifiers.type + identifiers.value
attachments.item_id
notes.item_id
```

## 5.2 搜索优化索引

第一版可先使用 LIKE + 关键词表 / 别名表。

后期可增加：

```text
SQLite FTS5
拼音搜索字段
搜索关键词缓存表
向量搜索索引
```

---

# 6. 推荐默认数据

## 6.1 默认分类

```text
元器件        slug=components      prefix=ELE
3D打印耗材    slug=filament        prefix=FIL
工具          slug=tools           prefix=TOOL
备用材料      slug=materials       prefix=MAT
线材          slug=cables          prefix=CAB
其他          slug=others          prefix=OTH
```

## 6.2 默认根位置

```text
name=工坊
code=WS
full_code=WS
type=room
```

## 6.3 默认状态

```text
normal     正常
low        少量
empty      已用完
broken     损坏
missing    找不到
idle       闲置
archived   已归档
```

---

# 7. 数据模型边界说明

## 7.1 不在核心系统中管理的数据

以下内容不放入 MVP 核心数据模型：

```text
机械臂坐标
抓取点
运动规划
真实地图坐标
标签打印模板细节
NFC 读写硬件配置
AI 提示词执行历史
采购审批流程
供应商管理
复杂财务统计
```

这些能力可以通过后续独立模块实现，并通过以下稳定标识关联核心系统：

```text
item.code
location.full_code
identifier.value
```

---

# 8. 后端实现建议

推荐后端目录结构：

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── response.py
│   ├── models/
│   │   ├── item.py
│   │   ├── category.py
│   │   ├── location.py
│   │   ├── attribute.py
│   │   ├── tag.py
│   │   ├── note.py
│   │   ├── attachment.py
│   │   ├── identifier.py
│   │   └── backup.py
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── api/
│   └── utils/
├── data/
│   ├── db.sqlite3
│   ├── uploads/
│   └── backups/
└── requirements.txt
```

核心原则：

```text
Router 层只处理请求和响应
Service 层处理业务逻辑
Repository 层处理数据库访问
CLI 只调用 API
```

---

# 9. 前端实现建议

推荐前端目录结构：

```text
frontend/
├── src/
│   ├── api/
│   │   ├── items.ts
│   │   ├── categories.ts
│   │   ├── locations.ts
│   │   ├── search.ts
│   │   └── backups.ts
│   ├── components/
│   │   ├── layout/
│   │   ├── item/
│   │   ├── location/
│   │   ├── search/
│   │   └── common/
│   ├── views/
│   │   ├── HomeView.vue
│   │   ├── ItemListView.vue
│   │   ├── ItemDetailView.vue
│   │   ├── LocationView.vue
│   │   └── SettingsView.vue
│   ├── stores/
│   ├── router/
│   └── utils/
├── public/
└── package.json
```

UI 风格：

```text
卡片式物品库
顶部搜索
左侧分类
中间物品列表
右侧详情抽屉
底部 / 独立位置视图
手机端单独适配
```

---

# 第二部分：后端开发 Prompt

以下 Prompt 可用于让 AI 辅助开发“工坊物栈”后端。

## 后端开发 Prompt

```text
你是一名经验丰富的后端架构师和 Python FastAPI 开发工程师。现在需要帮助我开发一个名为“工坊物栈”的个人工坊资源管理系统后端。

系统定位：
“工坊物栈”是部署在 Ubuntu 香橙派上的个人工坊资源管理框架，用于轻量管理元器件、3D 打印耗材、工具、备用材料、线材及其他工坊物品。系统不是工厂化库存系统，不做严格入库单、出库单、审批、采购、供应商管理等复杂流程，而是强调快速记录、快速查找、灵活修改、位置清楚、图片附件完整、API/CLI 可调用和后续模块可扩展。

技术栈要求：
- Python
- FastAPI
- SQLite
- SQLAlchemy 或 SQLModel
- Pydantic
- Uvicorn
- 本地文件系统保存图片和附件
- 后续 CLI、AI、扫码、NFC、标签打印、位置地图等模块统一通过 API 接入

架构要求：
- 采用 API First 设计
- Web 前端、CLI、外部模块都通过 REST API 调用
- CLI 不允许直连数据库
- 后端分层：Router → Service → Repository → Database / FileSystem
- Router 层不要写复杂业务逻辑
- Service 层负责业务规则、校验、日志记录
- Repository 层负责数据库访问
- 所有 API 返回统一结构：
  成功：{"success": true, "data": ..., "message": "ok"}
  失败：{"success": false, "error": {"code": "...", "message": "..."}}

核心数据模型：
1. categories：分类表，支持一级、二级和自定义分类。字段包括 id、name、slug、code_prefix、parent_id、sort_order、description、is_system、created_at、updated_at。
2. locations：位置表，支持层级位置和统一编号。字段包括 id、name、code、full_code、parent_id、type、description、sort_order、created_at、updated_at。位置系统只管理逻辑位置和 full_code，不管理机械臂坐标或物理抓取数据。
3. items：物品主表。字段包括 id、code、name、category_id、location_id、location_text、quantity、unit、status、description、need_restock、is_favorite、cover_attachment_id、is_archived、created_at、updated_at。
4. attribute_definitions：分类字段模板表。字段包括 id、category_id、name、key、field_type、unit、options_json、required、sort_order、is_enabled、created_at、updated_at。
5. item_attribute_values：物品自定义属性值表。字段包括 id、item_id、attribute_definition_id、name、key、value、value_type、unit、sort_order、created_at、updated_at。
6. tags 与 item_tags：标签和物品标签关联。
7. aliases：物品别名，用于模糊搜索。
8. notes：轻量备注和操作记录，字段包括 item_id、note_type、content、quantity_change、quantity_after、source、operator、metadata_json、created_at。
9. attachments：图片和附件元信息，实际文件存本地 uploads 目录。
10. identifiers：二维码、NFC、条形码等外部标识绑定。
11. api_tokens：API Token 表，只保存 Token 哈希。
12. backups：备份记录表。
13. system_settings：系统配置表。

编号规则：
- 物品编号不要使用中文，使用 ELE-000001、FIL-000001、TOOL-000001、MAT-000001、CAB-000001、OTH-000001 形式。
- 分类中文只作为显示名称，slug 和 code_prefix 使用英文、拼音或大写缩写。
- 位置编号使用层级 full_code，例如 WS.CAB-A.S02.G03。
- full_code 全局唯一，同级 code 唯一。

默认数据：
- 默认分类：元器件 ELE、3D打印耗材 FIL、工具 TOOL、备用材料 MAT、线材 CAB、其他 OTH。
- 默认根位置：工坊，code=WS，full_code=WS。
- 默认状态：normal、low、empty、broken、missing、idle、archived。

核心 API：
- GET /api/items
- POST /api/items
- GET /api/items/{id_or_code}
- PATCH /api/items/{id_or_code}
- DELETE /api/items/{id_or_code}
- POST /api/items/{id_or_code}/move
- POST /api/items/{id_or_code}/add
- POST /api/items/{id_or_code}/use
- POST /api/items/{id_or_code}/adjust
- POST /api/items/{id_or_code}/mark-restock
- POST /api/items/{id_or_code}/unmark-restock
- POST /api/items/{id_or_code}/favorite
- POST /api/items/{id_or_code}/unfavorite
- GET /api/categories
- GET /api/categories/tree
- POST /api/categories
- PATCH /api/categories/{id}
- DELETE /api/categories/{id}
- GET /api/locations
- GET /api/locations/tree
- POST /api/locations
- GET /api/locations/{id}
- GET /api/locations/by-code/{full_code}
- GET /api/locations/by-code/{full_code}/items
- PATCH /api/locations/{id}
- DELETE /api/locations/{id}
- GET /api/search?q=xxx
- POST /api/items/{id_or_code}/images
- POST /api/items/{id_or_code}/attachments
- GET /api/items/{id_or_code}/attachments
- DELETE /api/attachments/{id}
- POST /api/items/{id_or_code}/identifiers
- GET /api/items/by-identifier/{identifier}
- POST /api/backups
- GET /api/backups
- POST /api/backups/{backup_id}/restore
- GET /api/health
- GET /api/system/info

认证要求：
- 支持 AUTH_LOGIN_ENABLED、API_TOKEN_ENABLED、API_TOKEN_REQUIRE_ALL 配置项。
- 第一版可以不做复杂网页登录，但 API Token 必须保留。
- Token 通过 Authorization: Bearer <token> 传递。
- Token 不明文存储，只保存哈希。

搜索要求：
- 支持不完整输入和模糊匹配。
- 搜索范围包括名称、编号、分类、标签、别名、位置、备注、扩展属性、附件名。
- 第一版可以用 SQLite LIKE + 标签/别名/属性联合查询，后期预留 FTS5、拼音搜索、AI 语义搜索升级空间。

文件要求：
- 图片和附件不存入数据库。
- 数据库存储文件元信息。
- 本地目录结构：data/uploads/images、data/uploads/attachments、data/uploads/thumbnails、data/backups。
- 物品列表使用缩略图。

备份要求：
- 第一版必须实现备份。
- 备份内容包括 SQLite 数据库、uploads 文件目录、配置文件。
- 恢复备份前应自动创建当前快照。

开发任务：
请先帮我设计并生成后端项目骨架，包括：
1. FastAPI 项目结构
2. 数据库模型
3. Pydantic Schema
4. Repository 层
5. Service 层
6. API Router
7. 统一响应结构
8. API Token 校验中间件或依赖
9. 默认数据初始化脚本
10. 备份服务
11. 文件上传服务
12. 搜索服务
13. 基础测试用例

代码风格要求：
- 结构清晰，便于后续扩展
- 不要把业务逻辑堆在路由函数中
- 关键函数添加简洁注释
- 错误码使用大写蛇形命名，例如 ITEM_NOT_FOUND、LOCATION_NOT_FOUND、VALIDATION_ERROR
- 注意 SQLite 与香橙派部署环境的轻量化需求
- 不要引入 PostgreSQL、Redis、Celery 等第一版不需要的重型组件

请先输出项目目录结构和核心设计说明，然后再逐步生成代码。
```

---

# 第三部分：前端开发 Prompt

以下 Prompt 可用于让 AI 辅助开发“工坊物栈”前端。

## 前端开发 Prompt

```text
你是一名经验丰富的前端架构师和 Vue 3 开发工程师。现在需要帮助我开发一个名为“工坊物栈”的个人工坊资源管理系统前端。

系统定位：
“工坊物栈”是一个面向个人工坊的轻量化资源管理系统，用于管理元器件、3D 打印耗材、工具、备用材料、线材和其他物品。它不是工厂化库存后台，不追求严格入库、出库、审批、采购等流程，而是强调个人使用体验：快速记录、快速查找、清楚知道东西放在哪里、能看图片和备注、能快速修改数量和位置。

前端技术栈：
- Vue 3
- Vite
- TypeScript
- Tailwind CSS
- Pinia
- Vue Router
- Axios 或 Fetch 封装

前端风格要求：
- 做成现代、清爽、卡片式的个人工坊物品库
- 不要做成传统企业仓库后台
- 桌面端参考“左侧分类 + 顶部搜索 + 中间物品列表/卡片 + 右侧详情抽屉 + 下方/独立位置视图”的布局
- 手机端必须单独适配，不要把桌面布局直接缩小
- 重点突出搜索、快速新增、快速查看位置、快速修改数量/状态

桌面端主界面布局：
1. 左侧 Sidebar：分类、常用、需要补货、位置入口、设置入口
2. 顶部 TopBar：全局搜索框、快速新增按钮、备份/设置入口
3. 中间主区域：物品卡片列表，可切换列表/网格视图
4. 右侧详情抽屉：点击物品后展示详情，不必跳转页面
5. 位置视图：可以作为独立页面或主界面下方区域，展示位置树和位置下物品

手机端布局：
1. 顶部搜索框
2. 快捷按钮：新增、筛选、扫码预留
3. 主体：物品卡片流
4. 底部导航：物品、位置、常用、补货、设置
5. 详情页使用全屏页面或底部抽屉

核心页面：
- HomeView：工作台首页，展示搜索、最近修改、常用物品、需要补货
- ItemListView：物品列表，支持搜索、分类筛选、位置筛选、标签筛选
- ItemDetailDrawer / ItemDetailView：物品详情，展示图片、名称、编号、分类、位置、数量、状态、属性、标签、备注、附件
- ItemEditView / ItemFormDialog：新增和编辑物品
- LocationView：位置树、位置详情、位置下物品
- CategoryView：分类管理
- SettingsView：系统设置、API 地址、Token、备份入口
- BackupView：备份列表、创建备份、恢复备份

核心组件：
- AppLayout.vue
- AppSidebar.vue
- TopSearchBar.vue
- MobileBottomNav.vue
- ItemCard.vue
- ItemList.vue
- ItemDetailDrawer.vue
- ItemForm.vue
- QuickEditPanel.vue
- CategoryFilter.vue
- LocationTree.vue
- LocationPicker.vue
- TagList.vue
- AttributeEditor.vue
- AttachmentUploader.vue
- NoteTimeline.vue
- RestockBadge.vue
- StatusBadge.vue
- EmptyState.vue
- ConfirmDialog.vue

后端 API：
前端通过 REST API 调用后端，API 返回统一结构：
成功：{"success": true, "data": ..., "message": "ok"}
失败：{"success": false, "error": {"code": "...", "message": "..."}}

需要封装 API 客户端：
- 自动添加 Authorization: Bearer <token>
- 统一处理错误提示
- 统一解析 success/data/error
- API 地址可配置

核心 API 包括：
- GET /api/items
- POST /api/items
- GET /api/items/{id_or_code}
- PATCH /api/items/{id_or_code}
- DELETE /api/items/{id_or_code}
- POST /api/items/{id_or_code}/move
- POST /api/items/{id_or_code}/add
- POST /api/items/{id_or_code}/use
- POST /api/items/{id_or_code}/adjust
- POST /api/items/{id_or_code}/mark-restock
- POST /api/items/{id_or_code}/unmark-restock
- GET /api/categories/tree
- GET /api/locations/tree
- GET /api/locations/by-code/{full_code}/items
- GET /api/search?q=xxx
- POST /api/items/{id_or_code}/images
- POST /api/items/{id_or_code}/attachments
- GET /api/items/{id_or_code}/attachments
- POST /api/backups
- GET /api/backups

物品卡片显示内容：
- 封面图 / 占位图
- 名称
- 编号
- 分类
- 位置
- 数量 / 单位
- 状态
- 标签
- 是否需要补货
- 是否常用

物品详情显示内容：
- 大图
- 名称
- 编号
- 分类
- 结构化位置 full_code + 显示路径
- 自由位置文本
- 数量 / 单位
- 状态
- 自定义属性
- 标签
- 别名
- 备注时间线
- 图片和附件
- 快速操作按钮：移动、使用、调整、补货、常用、编辑

快速新增要求：
默认只显示必要字段：
- 名称
- 分类
- 位置
- 数量
- 单位
- 照片
- 备注

高级字段折叠显示：
- 自定义属性
- 标签
- 别名
- 附件
- 自由位置文本

搜索要求：
- 顶部搜索框始终易访问
- 支持输入不完整关键词
- 搜索结果显示匹配物品的名称、位置、数量、状态、封面图
- 搜索应能匹配名称、编号、分类、标签、别名、位置、备注和属性

交互原则：
- 不要让用户每次操作都像填仓库单据
- “使用”“增加”“调整”要做成轻量弹窗
- 支持模糊备注，例如“大概用了半卷”
- 位置既支持从位置树选择，也支持填写自由位置文本
- 错误提示要明确，不要只显示失败

视觉设计：
- 现代、简洁、偏个人工具软件
- 卡片圆角、适度阴影、良好留白
- 颜色不要过多
- 补货、低库存、损坏等状态用徽标提示
- 移动端点击区域要足够大
- 表格不是主视图，卡片和列表优先

开发任务：
请先帮我设计并生成前端项目骨架，包括：
1. Vite + Vue 3 + TypeScript 项目结构
2. Tailwind CSS 配置
3. 路由设计
4. Pinia store 设计
5. API client 封装
6. 主布局 AppLayout
7. 桌面 Sidebar + TopBar
8. 移动端 BottomNav
9. 物品列表和物品卡片
10. 物品详情抽屉
11. 快速新增 / 编辑表单
12. 位置树组件
13. 搜索组件
14. 基础空状态和错误提示组件

代码风格要求：
- 组件拆分清晰
- TypeScript 类型完整
- API 调用集中封装，不要散落在组件中
- UI 逻辑和数据请求适当分离
- 优先保证功能清晰和易维护，不追求复杂动画
- 不要加入第一版不需要的复杂数据可视化、3D 地图或企业后台报表

请先输出前端目录结构、页面结构和组件设计说明，然后再逐步生成代码。
```

---

# 10. 后续建议

完成本文档后，建议下一步按以下顺序推进开发：

```text
1. 建立后端项目骨架
2. 实现数据库模型和默认数据初始化
3. 实现物品、分类、位置三大基础 API
4. 实现搜索、备注、附件和备份
5. 实现 CLI 最小版本
6. 建立前端项目骨架
7. 实现主界面、物品卡片、详情抽屉、快速新增
8. 在真实工坊数据中试用并调整字段
```

第一版目标不是功能堆满，而是尽快形成一个能实际使用的闭环：

```text
新增物品 → 上传照片 → 记录位置 → 搜索找到 → 快速修改 → 备份保护
```

