# 工坊物栈 API / CLI 对照设计

## 1. 文档目的

本文档用于定义“工坊物栈”系统第一版 MVP 中核心功能对应的 API 与 CLI 命令。系统采用 API First / CLI First 的设计方式，Web 前端、CLI 工具以及后续 AI、扫码、NFC、标签打印、位置地图等独立模块均应通过统一 API 接入系统能力。

本系统不以工厂化库存流程为目标，而是面向个人工坊使用，强调快速记录、快速查找、轻量修改、低维护成本和后续扩展能力。

---

## 2. 总体原则

### 2.1 API 是能力入口

系统中的业务能力必须优先通过 API 暴露。Web 前端只是 API 的一个客户端，不能把核心业务逻辑写死在前端。

所有核心操作应遵循：

```text
客户端 / 外部模块 → REST API → Service 业务层 → Repository 数据访问层 → SQLite / 文件系统
```

### 2.2 CLI 统一调用 API

CLI 不允许直接访问数据库，也不应绕过后端业务逻辑。CLI 本质上是 API 的命令行客户端。

推荐调用关系：

```text
CLI → REST API → Service → Database / Files
```

这样可以保证 Web、CLI、AI 模块、扫码模块等所有入口使用同一套校验规则、权限规则和日志规则。

### 2.3 API 按业务动作设计

API 应对应真实业务动作，而不是前端按钮或界面行为。

正确示例：

```text
新增物品
移动位置
调整数量
标记补货
上传附件
搜索物品
创建备份
```

错误示例：

```text
打开弹窗
关闭抽屉
切换列表视图
切换 Tab
```

---

## 3. 统一命名约定

### 3.1 API 前缀

所有 API 使用统一前缀：

```http
/api
```

例如：

```http
GET /api/items
POST /api/items/{id}/move
```

### 3.2 CLI 命令名

建议 CLI 命令名使用：

```bash
stash
```

命令结构采用：

```bash
stash <resource> <action> [options]
```

示例：

```bash
stash item list
stash item show FIL-000001
stash item move FIL-000001 --to WS.DRY-A.G03
```

### 3.3 资源命名

API 路由资源名使用复数小写形式：

```text
items
categories
locations
tags
attachments
backups
```

CLI 资源名使用单数形式，便于输入：

```text
item
category
location
tag
attachment
backup
```

---

## 4. 通用返回结构

### 4.1 成功返回

所有 API 推荐使用统一成功结构：

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

列表返回示例：

```json
{
  "success": true,
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20
  },
  "message": "ok"
}
```

### 4.2 错误返回

```json
{
  "success": false,
  "error": {
    "code": "ITEM_NOT_FOUND",
    "message": "物品不存在"
  }
}
```

### 4.3 CLI 输出

CLI 默认输出人类可读格式。

示例：

```bash
stash search PLA
```

输出：

```text
FIL-000001  黑色 PLA      WS.DRY-A.G03     约 0.42 kg
FIL-000002  白色 PLA+     WS.SHELF-A.S01   半卷
```

CLI 必须支持 JSON 输出：

```bash
stash search PLA --json
stash item show FIL-000001 --json
```

JSON 输出直接对应 API 返回中的 `data` 字段，便于 AI、自动化脚本和外部模块调用。

---

## 5. 认证与配置

### 5.1 系统认证配置

认证采用配置项控制。

推荐配置：

```env
AUTH_LOGIN_ENABLED=false
API_TOKEN_ENABLED=true
API_TOKEN_REQUIRE_ALL=true
```

含义：

| 配置项 | 说明 |
|---|---|
| `AUTH_LOGIN_ENABLED` | 是否启用网页登录 |
| `API_TOKEN_ENABLED` | 是否启用 API Token |
| `API_TOKEN_REQUIRE_ALL` | 是否所有 API 都必须携带 Token |

第一版建议：

```text
网页登录可选，API Token 必须保留。
```

### 5.2 API Token 传递方式

推荐使用 Header：

```http
Authorization: Bearer <token>
```

### 5.3 CLI 配置

CLI 需要保存 API 地址和 Token。

```bash
stash config set api_url http://orangepi.local:8000
stash config set token xxxxx
stash config get api_url
stash config show
```

CLI 配置建议存放在用户目录，例如：

```text
~/.workshop-stash/config.toml
```

---

# 6. 物品管理 API / CLI

## 6.1 获取物品列表

### API

```http
GET /api/items
```

### 查询参数

| 参数 | 说明 |
|---|---|
| `q` | 搜索关键词 |
| `category` | 分类 ID、slug 或名称 |
| `location` | 位置 ID 或 full_code |
| `tag` | 标签 |
| `need_restock` | 是否需要补货 |
| `favorite` | 是否常用 |
| `page` | 页码 |
| `page_size` | 每页数量 |

### CLI

```bash
stash item list
stash item list --category 元器件
stash item list --location WS.DRY-A.G03
stash item list --restock
stash item list --favorite
stash item list --json
```

---

## 6.2 新增物品

### API

```http
POST /api/items
```

### 请求示例

```json
{
  "name": "黑色 PLA",
  "category": "3D打印耗材",
  "location_code": "WS.DRY-A.G03",
  "location_text": "干燥箱 A 的 03 格",
  "quantity": 0.42,
  "unit": "kg",
  "status": "normal",
  "description": "这卷容易拉丝，建议打印前烘干",
  "attributes": [
    {"name": "材料", "key": "material", "value": "PLA"},
    {"name": "颜色", "key": "color", "value": "黑色"},
    {"name": "线径", "key": "diameter", "value": "1.75", "unit": "mm"}
  ],
  "tags": ["PLA", "黑色", "已开封"]
}
```

### CLI

```bash
stash item add \
  --name "黑色 PLA" \
  --category "3D打印耗材" \
  --location WS.DRY-A.G03 \
  --quantity 0.42 \
  --unit kg \
  --tag PLA \
  --tag 黑色 \
  --attr 材料=PLA \
  --attr 颜色=黑色 \
  --attr 线径=1.75mm \
  --note "这卷容易拉丝，建议打印前烘干"
```

---

## 6.3 查看物品详情

### API

```http
GET /api/items/{item_id_or_code}
```

`item_id_or_code` 可以是数据库 ID，也可以是稳定编号，如：

```text
FIL-000001
```

### CLI

```bash
stash item show FIL-000001
stash item show 12
stash item show FIL-000001 --json
```

---

## 6.4 修改物品基础信息

### API

```http
PATCH /api/items/{item_id_or_code}
```

### 请求示例

```json
{
  "name": "黑色 PLA 耗材",
  "description": "打印前建议烘干 4 小时",
  "status": "normal",
  "is_favorite": true
}
```

### CLI

```bash
stash item update FIL-000001 --name "黑色 PLA 耗材"
stash item update FIL-000001 --status normal
stash item update FIL-000001 --note "打印前建议烘干 4 小时"
```

---

## 6.5 删除物品

### API

```http
DELETE /api/items/{item_id_or_code}
```

建议第一版采用软删除，避免误删。

### CLI

```bash
stash item delete FIL-000001
stash item delete FIL-000001 --force
```

---

# 7. 物品业务动作 API / CLI

业务动作接口用于给 Web、CLI、AI、扫码模块等调用。相比通用 `PATCH /api/items/{id}`，业务动作接口语义更明确。

---

## 7.1 移动物品位置

### API

```http
POST /api/items/{item_id_or_code}/move
```

### 请求示例

```json
{
  "location_code": "WS.CAB-A.S02.G03",
  "location_text": "A 柜第二层 03 格",
  "note": "整理耗材时移动"
}
```

### CLI

```bash
stash item move FIL-000001 --to WS.CAB-A.S02.G03
stash item move FIL-000001 --to-text "桌子右边小盒子"
```

---

## 7.2 增加数量

### API

```http
POST /api/items/{item_id_or_code}/add
```

### 请求示例

```json
{
  "amount": 1,
  "unit": "卷",
  "note": "新买一卷黑色 PLA"
}
```

### CLI

```bash
stash item add-qty FIL-000001 --amount 1 --unit 卷 --note "新买一卷"
```

说明：这里 CLI 不使用 `stash item add`，避免和新增物品混淆。

---

## 7.3 使用 / 消耗数量

### API

```http
POST /api/items/{item_id_or_code}/use
```

### 请求示例

```json
{
  "amount": 0.12,
  "unit": "kg",
  "note": "打印外壳用掉一些"
}
```

### CLI

```bash
stash item use FIL-000001 --amount 0.12 --unit kg --note "打印外壳"
```

---

## 7.4 直接调整数量

### API

```http
POST /api/items/{item_id_or_code}/adjust
```

### 请求示例

```json
{
  "quantity": 0.42,
  "unit": "kg",
  "note": "重新称重后修正"
}
```

### CLI

```bash
stash item adjust FIL-000001 --quantity 0.42 --unit kg --note "重新称重"
```

---

## 7.5 标记需要补货

### API

```http
POST /api/items/{item_id_or_code}/mark-restock
```

### CLI

```bash
stash item restock FIL-000001
```

---

## 7.6 取消补货标记

### API

```http
POST /api/items/{item_id_or_code}/unmark-restock
```

### CLI

```bash
stash item unstock FIL-000001
```

---

## 7.7 标记常用

### API

```http
POST /api/items/{item_id_or_code}/favorite
```

### CLI

```bash
stash item favorite FIL-000001
```

---

## 7.8 取消常用

### API

```http
POST /api/items/{item_id_or_code}/unfavorite
```

### CLI

```bash
stash item unfavorite FIL-000001
```

---

# 8. 分类管理 API / CLI

## 8.1 获取分类列表

### API

```http
GET /api/categories
GET /api/categories/tree
```

### CLI

```bash
stash category list
stash category tree
stash category list --json
```

---

## 8.2 新增分类

### API

```http
POST /api/categories
```

### 请求示例

```json
{
  "name": "树脂材料",
  "slug": "resin-material",
  "code_prefix": "RES",
  "parent_id": null
}
```

### CLI

```bash
stash category add "树脂材料" --slug resin-material --prefix RES
stash category add "PLA" --parent "3D打印耗材" --slug pla --prefix FIL
```

---

## 8.3 修改分类

### API

```http
PATCH /api/categories/{category_id}
```

### CLI

```bash
stash category update 3 --name "3D打印耗材"
stash category update 3 --prefix FIL
```

---

## 8.4 删除分类

### API

```http
DELETE /api/categories/{category_id}
```

删除前应检查该分类下是否存在物品。建议默认禁止删除非空分类。

### CLI

```bash
stash category delete 3
stash category delete 3 --force
```

---

# 9. 位置管理 API / CLI

位置系统只负责逻辑位置和统一编号，不管理机械臂坐标、抓取点或运动规划。

---

## 9.1 获取位置列表

### API

```http
GET /api/locations
GET /api/locations/tree
```

### CLI

```bash
stash location list
stash location tree
stash location list --json
```

---

## 9.2 新增位置

### API

```http
POST /api/locations
```

### 请求示例

```json
{
  "name": "03格",
  "code": "G03",
  "parent_code": "WS.CAB-A.S02",
  "type": "grid",
  "description": "A柜第二层 03 格"
}
```

系统自动生成：

```text
full_code = WS.CAB-A.S02.G03
```

### CLI

```bash
stash location add "工坊" --code WS --type room
stash location add "A柜" --code CAB-A --parent WS --type cabinet
stash location add "第二层" --code S02 --parent WS.CAB-A --type shelf
stash location add "03格" --code G03 --parent WS.CAB-A.S02 --type grid
```

---

## 9.3 查看位置详情

### API

```http
GET /api/locations/{location_id}
GET /api/locations/by-code/{full_code}
```

### CLI

```bash
stash location show WS.CAB-A.S02.G03
stash location show 12
```

---

## 9.4 查看某位置下的物品

### API

```http
GET /api/locations/{location_id}/items
GET /api/locations/by-code/{full_code}/items
```

### CLI

```bash
stash location items WS.CAB-A.S02.G03
```

---

## 9.5 修改位置

### API

```http
PATCH /api/locations/{location_id}
```

### CLI

```bash
stash location update WS.CAB-A.S02.G03 --name "03号格"
stash location update WS.CAB-A.S02.G03 --description "常放耗材配件"
```

说明：位置 `code` 修改要谨慎，因为它会影响 `full_code` 和外部模块绑定。建议第一版允许修改显示名称，限制修改 code。

---

## 9.6 删除位置

### API

```http
DELETE /api/locations/{location_id}
```

删除前应检查：

```text
该位置是否有子位置
该位置是否绑定物品
```

默认禁止删除非空位置。

### CLI

```bash
stash location delete WS.CAB-A.S02.G03
stash location delete WS.CAB-A.S02.G03 --force
```

---

# 10. 自定义属性 API / CLI

## 10.1 获取属性模板

### API

```http
GET /api/attribute-definitions
GET /api/categories/{category_id}/attribute-definitions
```

### CLI

```bash
stash attr-def list
stash attr-def list --category "3D打印耗材"
```

---

## 10.2 新增属性模板

### API

```http
POST /api/attribute-definitions
```

### 请求示例

```json
{
  "category_id": 2,
  "name": "线径",
  "key": "diameter",
  "field_type": "number",
  "unit": "mm",
  "required": false,
  "sort_order": 10
}
```

### CLI

```bash
stash attr-def add --category "3D打印耗材" --name "线径" --key diameter --type number --unit mm
```

---

## 10.3 修改属性模板

### API

```http
PATCH /api/attribute-definitions/{id}
```

### CLI

```bash
stash attr-def update 5 --name "耗材线径"
stash attr-def update 5 --unit mm
```

---

## 10.4 删除属性模板

### API

```http
DELETE /api/attribute-definitions/{id}
```

如果已有物品使用该字段，建议不物理删除，只禁用或隐藏。

### CLI

```bash
stash attr-def delete 5
stash attr-def disable 5
```

---

# 11. 标签与别名 API / CLI

## 11.1 标签管理

### API

```http
GET    /api/tags
POST   /api/tags
DELETE /api/tags/{id}
```

### CLI

```bash
stash tag list
stash tag add PLA
stash tag delete PLA
```

---

## 11.2 给物品添加标签

### API

```http
POST /api/items/{item_id_or_code}/tags
```

### 请求示例

```json
{
  "tags": ["PLA", "黑色", "已开封"]
}
```

### CLI

```bash
stash item tag FIL-000001 PLA
stash item tag FIL-000001 黑色
```

---

## 11.3 移除物品标签

### API

```http
DELETE /api/items/{item_id_or_code}/tags/{tag}
```

### CLI

```bash
stash item untag FIL-000001 PLA
```

---

## 11.4 别名管理

别名用于增强搜索。例如 ESP32-S3 可以有别名“开发板”“乐鑫”“WiFi模块”。

### API

```http
GET  /api/items/{item_id_or_code}/aliases
POST /api/items/{item_id_or_code}/aliases
DELETE /api/items/{item_id_or_code}/aliases/{alias}
```

### CLI

```bash
stash item alias FIL-000001 "耗材"
stash item alias ELE-000003 "开发板"
stash item unalias ELE-000003 "开发板"
```

---

# 12. 备注记录 API / CLI

## 12.1 获取物品记录

### API

```http
GET /api/items/{item_id_or_code}/notes
```

### CLI

```bash
stash note list FIL-000001
```

---

## 12.2 新增备注记录

### API

```http
POST /api/items/{item_id_or_code}/notes
```

### 请求示例

```json
{
  "note_type": "note",
  "content": "这卷 PLA 打印前建议烘干",
  "source": "cli"
}
```

### CLI

```bash
stash note add FIL-000001 "这卷 PLA 打印前建议烘干"
stash note add FIL-000001 "移动到干燥箱" --type move
```

---

# 13. 图片与附件 API / CLI

## 13.1 上传图片

### API

```http
POST /api/items/{item_id_or_code}/images
```

使用 `multipart/form-data` 上传。

### CLI

```bash
stash image add FIL-000001 ./pla.jpg
stash image add FIL-000001 ./pla.jpg --cover
```

---

## 13.2 上传附件

### API

```http
POST /api/items/{item_id_or_code}/attachments
```

### CLI

```bash
stash file add ELE-000003 ./datasheet.pdf
stash file add TOOL-000002 ./manual.pdf
```

---

## 13.3 获取附件列表

### API

```http
GET /api/items/{item_id_or_code}/attachments
```

### CLI

```bash
stash file list ELE-000003
```

---

## 13.4 删除附件

### API

```http
DELETE /api/attachments/{attachment_id}
```

### CLI

```bash
stash file delete 18
```

---

# 14. 搜索 API / CLI

搜索是工坊物栈的核心功能之一，需要支持不完整输入和模糊匹配。

## 14.1 全局搜索

### API

```http
GET /api/search?q={keyword}
```

### 查询参数

| 参数 | 说明 |
|---|---|
| `q` | 搜索关键词 |
| `category` | 分类限制 |
| `location` | 位置限制 |
| `limit` | 返回数量 |
| `include_archived` | 是否包含已归档物品 |

### 搜索范围

```text
名称
编号
分类
标签
别名
位置
备注
扩展属性
附件名
```

### CLI

```bash
stash search PLA
stash search esp32
stash search "M3 螺丝"
stash search pla --category "3D打印耗材"
stash search esp --json
```

---

## 14.2 根据外部标识查询

用于二维码、NFC、条形码等模块。

### API

```http
GET /api/items/by-identifier/{identifier}
```

### CLI

```bash
stash item find-id QR-FIL-000001
stash item find-id NFC-04AABBCCDD
```

---

# 15. 外部标识 API / CLI

## 15.1 绑定外部标识

### API

```http
POST /api/items/{item_id_or_code}/identifiers
```

### 请求示例

```json
{
  "type": "qrcode",
  "value": "QR-FIL-000001",
  "description": "耗材标签二维码"
}
```

### CLI

```bash
stash item bind FIL-000001 --type qrcode --value QR-FIL-000001
stash item bind FIL-000001 --type nfc --value 04AABBCCDD
```

---

## 15.2 解除外部标识

### API

```http
DELETE /api/items/{item_id_or_code}/identifiers/{identifier_id}
```

### CLI

```bash
stash item unbind FIL-000001 --value QR-FIL-000001
```

---

# 16. 备份 API / CLI

备份必须作为第一版核心功能实现。

## 16.1 创建备份

### API

```http
POST /api/backups
```

### 请求示例

```json
{
  "include_uploads": true,
  "note": "手动备份"
}
```

### CLI

```bash
stash backup create
stash backup create --note "修改分类前备份"
```

---

## 16.2 查看备份列表

### API

```http
GET /api/backups
```

### CLI

```bash
stash backup list
```

---

## 16.3 恢复备份

### API

```http
POST /api/backups/{backup_id}/restore
```

恢复前应自动创建当前数据快照，避免误恢复。

### CLI

```bash
stash backup restore backup-20260514-103000
```

---

## 16.4 下载备份

### API

```http
GET /api/backups/{backup_id}/download
```

### CLI

```bash
stash backup download backup-20260514-103000 --output ./backup.zip
```

---

# 17. 系统信息 API / CLI

## 17.1 系统健康检查

### API

```http
GET /api/health
```

### CLI

```bash
stash ping
```

---

## 17.2 查看系统信息

### API

```http
GET /api/system/info
```

### CLI

```bash
stash system info
```

返回内容可包括：

```text
系统版本
数据库路径
上传目录
备份目录
认证状态
物品数量
位置数量
最近备份时间
```

---

# 18. 第一版 API / CLI 优先级

## P0：必须实现

```text
物品新增、查看、修改、删除
物品移动位置
增加 / 使用 / 调整数量
分类管理
位置管理
搜索
图片上传
备注记录
备份
API Token
CLI 配置
```

## P1：建议实现

```text
标签
别名
附件上传
补货标记
常用标记
外部标识绑定
JSON 输出
```

## P2：后续实现

```text
二维码生成
标签打印
NFC 绑定
位置地图布局
AI 调用封装
批量导入导出
```

---

# 工坊物栈 API / CLI 扩展设计规范

## 1. 文档目的

本文档用于规定日后为“工坊物栈”新增 API 或 CLI 命令时必须遵守的设计规范，避免系统在后续扩展 AI、扫码、NFC、标签打印、位置地图、自动化工具等模块时出现接口混乱、命令风格不一致、业务逻辑重复等问题。

---

## 2. 总体设计原则

### 2.1 API First

任何新增核心能力都必须先设计 API。Web 前端和 CLI 都是 API 的客户端，不能绕过 API 直接操作数据库或文件。

### 2.2 CLI First

凡是系统中高频、可自动化、可脚本化的业务动作，都应提供 CLI 命令。

例如：

```text
搜索物品
新增物品
移动位置
调整数量
创建备份
```

不需要为纯 UI 行为提供 CLI，例如：

```text
展开详情栏
切换暗色模式
关闭弹窗
```

### 2.3 Service First

API 路由层不能直接写复杂业务逻辑。新增功能必须优先落在 Service 层，API 和 CLI 共同调用同一套业务能力。

推荐结构：

```text
API Router → Service → Repository → Database / Files
CLI Client → API Router → Service → Repository → Database / Files
```

### 2.4 不直连数据库

CLI、外部模块、AI 模块、扫码模块、NFC 模块均不得直接访问 SQLite 数据库。

原因：

```text
避免绕过权限和 Token
避免绕过数据校验
避免业务规则重复
避免数据库结构变动影响外部模块
便于远程调用香橙派系统
```

---

## 3. 新增 API 的判断标准

新增 API 前必须确认它属于业务动作，而不是界面动作。

### 应该新增 API 的情况

```text
新增一种可复用业务能力
后续外部模块可能调用
CLI 需要执行该能力
该能力会修改数据库或文件
该能力需要统一权限、日志或校验
```

示例：

```text
生成标签打印数据
批量导入物品
绑定 NFC 标识
创建位置地图布局
让 AI 查询某类物品
```

### 不应该新增 API 的情况

```text
只是前端展示状态变化
只是打开或关闭弹窗
只是切换卡片 / 表格视图
只是前端本地排序
只是临时 UI 交互
```

---

## 4. API 路由设计规范

### 4.1 路由命名

资源型 API 使用名词复数：

```http
GET /api/items
POST /api/items
GET /api/locations
```

动作型 API 使用业务动词：

```http
POST /api/items/{id}/move
POST /api/items/{id}/adjust
POST /api/items/{id}/mark-restock
```

### 4.2 HTTP 方法使用规范

| 方法 | 用途 |
|---|---|
| `GET` | 查询资源，不产生副作用 |
| `POST` | 创建资源，或执行业务动作 |
| `PATCH` | 局部修改资源 |
| `PUT` | 整体替换资源，第一版尽量少用 |
| `DELETE` | 删除或归档资源 |

### 4.3 禁止使用含糊路由

不推荐：

```http
POST /api/do
POST /api/action
GET /api/item_op
POST /api/update_data
```

推荐：

```http
POST /api/items/{id}/move
POST /api/items/{id}/adjust
POST /api/backups
```

### 4.4 业务动作优先保持语义清晰

例如数量变化不要全部混成一个接口：

```http
POST /api/items/{id}/change-quantity
```

更推荐拆成：

```http
POST /api/items/{id}/add
POST /api/items/{id}/use
POST /api/items/{id}/adjust
```

原因：

```text
AI 更容易调用
CLI 更容易理解
日志记录更清楚
后续权限控制更细
```

---

## 5. CLI 命令设计规范

### 5.1 命令结构

统一采用：

```bash
stash <resource> <action> [options]
```

示例：

```bash
stash item show FIL-000001
stash location tree
stash backup create
```

### 5.2 资源名使用单数

推荐：

```bash
stash item list
stash category list
stash location list
```

不推荐：

```bash
stash items list
stash categories list
```

### 5.3 常用动作名称统一

| 动作 | CLI action |
|---|---|
| 列表 | `list` |
| 查看详情 | `show` |
| 新增资源 | `add` |
| 修改资源 | `update` |
| 删除资源 | `delete` |
| 移动位置 | `move` |
| 使用 / 消耗 | `use` |
| 调整数量 | `adjust` |
| 搜索 | `search` |
| 创建备份 | `backup create` |

### 5.4 避免命令歧义

新增物品使用：

```bash
stash item add
```

增加已有物品数量不应也叫 `add`，推荐：

```bash
stash item add-qty
```

使用 / 消耗物品：

```bash
stash item use
```

直接修正数量：

```bash
stash item adjust
```

### 5.5 CLI 必须支持 JSON 输出

任何查询类命令都应支持：

```bash
--json
```

示例：

```bash
stash item show FIL-000001 --json
stash search PLA --json
stash location tree --json
```

### 5.6 CLI 错误输出规范

CLI 人类可读错误示例：

```text
错误：物品不存在：FIL-999999
```

JSON 错误输出示例：

```json
{
  "success": false,
  "error": {
    "code": "ITEM_NOT_FOUND",
    "message": "物品不存在：FIL-999999"
  }
}
```

---

## 6. 数据输入规范

### 6.1 编号字段不得使用中文

稳定编号只允许：

```text
A-Z
0-9
-
_
.
```

中文只用于显示名称。

正确：

```text
name = 黑色 PLA
code = FIL-000001
location_full_code = WS.DRY-A.G03
```

不推荐：

```text
code = 耗材-黑色PLA-001
```

### 6.2 位置编号规范

位置使用层级编号：

```text
WS.CAB-A.S02.G03
```

规则：

```text
每一级有自己的 code
层级之间用 . 分隔
full_code 自动生成
同级 code 唯一
code 尽量创建后不修改
```

### 6.3 分类编号规范

分类可以显示中文，但必须具有稳定英文 / 拼音标识和编号前缀。

示例：

```text
name = 3D打印耗材
slug = filament
code_prefix = FIL
```

---

## 7. 请求与响应规范

### 7.1 API 请求体使用 JSON

除文件上传接口外，API 请求体统一使用 JSON。

文件上传使用：

```http
multipart/form-data
```

### 7.2 时间格式

所有时间使用 ISO 8601 格式：

```text
2026-05-14T10:30:00+08:00
```

### 7.3 数量字段

数量字段应允许小数。

示例：

```json
{
  "quantity": 0.42,
  "unit": "kg"
}
```

原因：3D 打印耗材、线材、备用材料常需要使用重量、长度等非整数数量。

### 7.4 备注字段

个人系统允许轻量、模糊备注，不要求工业化流程描述。

示例：

```text
大概用了半卷
重新称重，约 420g
放到桌子右边小盒子
```

---

## 8. 错误码规范

错误码采用大写蛇形命名。

示例：

```text
ITEM_NOT_FOUND
LOCATION_NOT_FOUND
CATEGORY_NOT_FOUND
INVALID_TOKEN
DUPLICATE_CODE
LOCATION_CODE_EXISTS
VALIDATION_ERROR
BACKUP_FAILED
UPLOAD_FAILED
```

错误返回结构：

```json
{
  "success": false,
  "error": {
    "code": "LOCATION_NOT_FOUND",
    "message": "位置不存在：WS.CAB-A.S02.G03"
  }
}
```

---

## 9. 日志与来源记录规范

所有会修改数据的业务动作都应记录来源。

建议字段：

```text
source
operator
metadata
created_at
```

`source` 可取值：

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

示例：

```json
{
  "source": "cli",
  "operator": "default",
  "metadata": {
    "command": "stash item move FIL-000001 --to WS.DRY-A.G03"
  }
}
```

这样后续排查问题时可以知道某个操作来自网页、CLI 还是外部模块。

---

## 10. 权限与 Token 规范

### 10.1 API Token 必须保留

即使网页登录关闭，API Token 也必须存在。

CLI、外部模块、AI 模块均通过 Token 调用 API。

### 10.2 不同外部模块建议使用不同 Token

后期可支持外部客户端表：

```text
external_clients
├── id
├── name
├── token_hash
├── enabled
├── description
├── created_at
```

示例：

```text
CLI
AI助手
扫码模块
NFC模块
标签打印模块
```

### 10.3 Token 不应明文存库

数据库中建议存储 Token 哈希，而不是明文 Token。

---

## 11. 文件接口规范

### 11.1 文件不存入数据库

数据库只保存文件元信息，实际文件存放在本地目录。

推荐结构：

```text
data/
├── uploads/
│   ├── images/
│   ├── attachments/
│   └── thumbnails/
└── backups/
```

### 11.2 文件上传必须记录所属资源

附件必须明确关联对象，例如：

```text
item_id
attachment_type
file_path
original_name
mime_type
size
uploaded_at
```

### 11.3 图片应支持缩略图

物品列表和卡片视图应使用缩略图，避免手机端加载过慢。

---

## 12. 搜索接口扩展规范

### 12.1 搜索应保持统一入口

全局搜索使用：

```http
GET /api/search?q={keyword}
```

后续增加 AI 语义搜索、拼音搜索、向量搜索时，也应尽量保持兼容。

### 12.2 搜索范围扩展必须可控

搜索范围包括：

```text
名称
编号
分类
标签
别名
位置
备注
扩展属性
附件名
```

新增搜索范围时应避免影响速度。必要时建立独立搜索索引表。

### 12.3 搜索结果应返回关键上下文

搜索结果至少包含：

```text
物品编号
名称
分类
位置
数量
状态
封面图
匹配原因
```

示例：

```json
{
  "code": "ELE-000003",
  "name": "ESP32-S3 模块",
  "location": "WS.CAB-A.S02.G03",
  "matched_by": ["name", "alias"]
}
```

---

## 13. 备份相关规范

### 13.1 备份是核心能力

新增影响数据结构或文件存储的功能时，必须考虑备份是否覆盖。

备份至少包括：

```text
SQLite 数据库
uploads 文件目录
配置文件
```

### 13.2 恢复前自动创建当前快照

执行恢复前，系统应自动创建当前状态备份，避免误恢复造成数据丢失。

### 13.3 新增模块不得私自存放关键数据

如果后续模块需要存储重要数据，应统一放入系统配置的数据目录，或提供自己的备份接口。

---

## 14. 外部模块接入规范

### 14.1 外部模块只通过 API 接入

包括但不限于：

```text
AI 助手
扫码模块
NFC 模块
标签打印模块
位置地图模块
称重模块
机械臂模块
自动化脚本
```

### 14.2 外部模块应使用稳定编号

外部模块不要依赖数据库自增 ID，优先使用：

```text
item.code
location.full_code
identifier.value
```

### 14.3 外部模块自有数据自行管理

核心系统只提供物品、分类、位置、标签、附件、搜索等基础能力。

例如机械臂模块需要坐标、抓取点和路径规划数据，应由机械臂模块自行管理，并通过 `location.full_code` 与核心系统关联。

---

## 15. 版本兼容规范

### 15.1 API 版本

第一版可以暂时不加版本前缀，但如果后续接口变化较大，建议升级为：

```http
/api/v1/items
/api/v1/search
```

### 15.2 不轻易破坏已有接口

已经公开给 CLI 或外部模块使用的接口，不应随意修改请求字段或返回结构。

如需调整，应：

```text
保留旧字段一段时间
增加新字段
标记 deprecated
更新文档和 CLI
```

---

## 16. 新增 API / CLI 的标准流程

新增任何功能时，建议按以下流程执行：

```text
1. 明确该功能是否属于业务动作
2. 设计 Service 层方法
3. 设计 API 路由与请求 / 响应结构
4. 设计 CLI 命令和参数
5. 确认是否需要记录 notes / operation_logs
6. 确认是否需要 Token 权限控制
7. 确认是否影响搜索
8. 确认是否影响备份
9. 编写测试
10. 更新 API / CLI 对照文档
```

---

## 17. 示例：新增“标签打印”功能时应如何设计

不应直接让前端拼接标签内容。

推荐设计：

### API

```http
POST /api/items/{id}/label-preview
POST /api/items/{id}/label-print
```

### CLI

```bash
stash label preview FIL-000001
stash label print FIL-000001 --template small
```

### 业务层

```text
label_service.generate_preview()
label_service.print_label()
```

### 说明

标签打印模块可以是外部服务，但应通过 API 获取物品编号、名称、位置编号等核心数据。

---

## 18. 示例：新增“AI 查询与操作”能力时应如何设计

AI 不应直接操作数据库，也不应绕过业务动作 API。

AI 应调用已有业务接口，例如：

```text
搜索物品 → GET /api/search?q=xxx
移动物品 → POST /api/items/{id}/move
标记补货 → POST /api/items/{id}/mark-restock
添加备注 → POST /api/items/{id}/notes
```

如果需要新增 AI 专用能力，应优先考虑是否可以复用已有 API。只有在确实需要编排多个动作时，才新增独立接口。

---

## 19. 最终规范总结

后续新增 API / CLI 时必须遵守以下原则：

```text
1. API 按业务动作设计，不按前端按钮设计
2. CLI 必须调用 API，不得直连数据库
3. 业务逻辑放在 Service 层，不堆在 Router 层
4. 稳定编号不用中文，中文只做显示名称
5. 所有修改操作应记录来源
6. 查询命令必须支持 JSON 输出
7. API 返回结构保持统一
8. 外部模块使用 Token 认证
9. 外部模块优先使用 item.code 和 location.full_code
10. 新功能必须考虑搜索、备份和后续扩展影响
```

这一规范的目标是让“工坊物栈”长期保持清晰、轻量、可扩展，而不是随着功能增加变成难以维护的混乱系统。

