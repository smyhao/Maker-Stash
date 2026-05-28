# 工坊物栈后端

第一阶段实现后端核心闭环：物品、分类、位置、搜索、备注、图片/附件、备份、API Token，以及完整 CLI 客户端。当前后端还包含关键写接口幂等、轻量审计、任务 API 和 plan / confirm 工作流基础能力。

## 初始化

```bash
cd backend
python -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.scripts.init_db
..\.venv\Scripts\python.exe -m app.scripts.create_token --name cli
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`create_token` 生成的明文 Token 只会显示一次。数据库只保存 Token 哈希；如果忘记明文，需要重新创建一个 Token，并在前端「设置 → 连接」和 CLI 配置中更新。

局域网部署时不要继续使用默认的 `127.0.0.1` 监听。推荐从项目根目录启动：

```bash
python start.py --lan --no-browser
```

后端和前端端口可以写在项目根目录的 `start.toml`：

```toml
lan = true
backend_port = 8000
frontend_port = 5173
no_browser = true
```

如只启动后端，可显式绑定所有网卡：

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端通过同机 `/api` 代理访问后端时不需要 CORS。若浏览器直接从 `http://<OrangePi局域网IP>:5173` 请求 `http://<OrangePi局域网IP>:8000`，请在 `backend/.env` 配置允许来源：

```env
CORS_ALLOWED_ORIGINS=http://<OrangePi局域网IP>:5173
```

## CLI 用法

CLI 作为 API 客户端调用后端，不直连数据库。配置保存在 `~/.workshop-stash/config.toml`。

```bash
# 配置
python -m app.cli.main config set api_url http://127.0.0.1:8000
python -m app.cli.main config set token <token>
python -m app.cli.main ping

# 物品
python -m app.cli.main item list
python -m app.cli.main item list --tag PLA --status normal --json
python -m app.cli.main item show FIL-000001
python -m app.cli.main item add --name "黑色 PLA" --category filament --quantity 0.42 --unit kg --tag PLA
python -m app.cli.main item add --name "ESP32" --category components --attr 型号=ESP32-S3
python -m app.cli.main item update FIL-000001 --name "黑色 PLA 耗材" --description "打印前烘干"
python -m app.cli.main item delete FIL-000001
python -m app.cli.main item delete FIL-000001 --force
python -m app.cli.main item move FIL-000001 --to WS.CAB-A.S02.G03
python -m app.cli.main item add-qty FIL-000001 --amount 1 --unit kg
python -m app.cli.main item use FIL-000001 --amount 0.12 --unit kg
python -m app.cli.main item adjust FIL-000001 --quantity 0.30 --unit kg
python -m app.cli.main item restock FIL-000001
python -m app.cli.main item unstock FIL-000001
python -m app.cli.main item favorite FIL-000001
python -m app.cli.main item tag ELE-000001 乐鑫 开发板
python -m app.cli.main item untag ELE-000001 乐鑫
python -m app.cli.main item alias ELE-000001 WiFi模块
python -m app.cli.main item unalias ELE-000001 WiFi模块
python -m app.cli.main item bind ELE-000001 --type qrcode --value QR-ELE-000001
python -m app.cli.main item unbind ELE-000001 5
python -m app.cli.main item find-id QR-ELE-000001
python -m app.cli.main note list FIL-000001
python -m app.cli.main note add FIL-000001 "打印前建议烘干"

# 分类
python -m app.cli.main category list
python -m app.cli.main category tree
python -m app.cli.main category add "树脂材料" --slug resin --prefix RES
python -m app.cli.main category add "电阻" --slug resistor --prefix RES --parent-id 1
python -m app.cli.main category update 3 --name "3D打印耗材"
python -m app.cli.main category delete 7

# 位置
python -m app.cli.main location list
python -m app.cli.main location tree
python -m app.cli.main location show WS.CAB-A
python -m app.cli.main location add "A柜" --code CAB-A --parent WS --type cabinet
python -m app.cli.main location update 2 --name "A号柜"
python -m app.cli.main location delete 5
python -m app.cli.main location items WS.CAB-A

# 标签
python -m app.cli.main tag list
python -m app.cli.main tag add PLA
python -m app.cli.main tag delete 3

# 属性模板
python -m app.cli.main attr-def list
python -m app.cli.main attr-def list --category-id 2
python -m app.cli.main attr-def add --category-id 2 --name 颜色 --key color --type text
python -m app.cli.main attr-def update 5 --name 耗材颜色
python -m app.cli.main attr-def delete 5

# 图片和附件
python -m app.cli.main image add FIL-000001 ./pla.jpg --cover
python -m app.cli.main file add ELE-000001 ./datasheet.pdf
python -m app.cli.main file list ELE-000001
python -m app.cli.main file delete 18

# 搜索
python -m app.cli.main search PLA
python -m app.cli.main search esp --category components --json
python -m app.cli.main search 螺丝 --location WS.CAB-A

# 备份
python -m app.cli.main backup create
python -m app.cli.main backup create --note "修改前备份"
python -m app.cli.main backup list
python -m app.cli.main backup restore backup-20260514-103000
python -m app.cli.main backup download backup-20260514-103000 --output backup.zip

# 系统
python -m app.cli.main system info
```

图片和附件限制：

- 单个上传文件最大 50MB，由 `app/core/config.py` 的 `max_upload_bytes` 控制。
- 图片上传只接受 JPEG、PNG、WebP、GIF；其他文件请使用 `file add`。
- `image add --cover` 会将该图片设置为物品封面。
- 删除附件会同步删除上传原文件和缩略图；如果删除的是封面，会同步清空物品封面引用。
- `item delete --force` 会归档物品并释放该物品所有附件文件；不带 `--force` 只归档物品，不删除附件文件。

备份恢复注意事项：

- `backup create` 默认包含上传文件；`--without-uploads` 只备份数据库。
- `backup restore` 恢复前会自动创建当前状态快照。
- 恢复会覆盖当前数据库和上传文件目录，建议先确认目标备份可下载、可离线保存。
- 同一时间只允许一个备份或恢复任务执行；如返回 `BACKUP_IN_PROGRESS`，等待当前任务完成后重试。

可通过 `pip install -e .` 安装后直接使用 `stash` 命令：

```bash
pip install -e .
stash item list
stash search PLA --json
```

## 搜索

全字段搜索覆盖 10 个维度：名称、编号、描述、分类、位置、标签、别名、备注、属性、附件名。

- `/api/search?q=xxx` — 搜索接口，支持 category/location/tag 过滤
- `/api/items?q=xxx` — 物品列表也使用全字段搜索
- `category` 过滤支持分类 slug、名称或 ID；传入父分类时会包含所有子分类和孙分类物品
- 搜索结果包含 `matched_by` 标记命中维度
- 前端全局搜索框基于 `/api/items?q=` 提供物品建议，下拉项可直接跳到库存详情。

## 分类与位置扩展

- 分类是树形结构。分类管理页可调整已有分类的父分类，用于把「电阻」「电容」等子类归入「元器件」；后端会拒绝把分类移动到自身或子分类下。
- 分类统计会把子分类物品汇总到父分类，库存页左侧分类栏可展开/收起子分类。
- 普通位置继续支持多物品承载；可视化收纳盒是位置树上的扩展能力。
- 可视化收纳盒支持 `grid` 和 `row` 两种布局。`grid` 自动生成 `A01...C05` 形式的格位，`row` 自动生成 `01...N` 形式的格位。
- 收纳盒外观颜色保存在 `appearance_color`，支持预设名 `sage/clay/sand/ink` 或自定义 `#RRGGBB` RGB 编号；前端用它渲染位置树色条、格位画布和布局预览。
- 格位是自动生成的叶子位置，不在普通 `/locations/tree` 中逐个展开；通过专用格位画布接口读取。
- 首版一个格位最多绑定一条未归档物品记录。移动到空格位使用物品移动接口；前端空格位可搜索并选择已有物品放入。已占格位之间交换必须使用收纳盒交换接口。
- 物品响应中的 `location_display` 可直接用于展示「透明分格盒 A · B03」这类结构化位置文本。

## 封面与资料附件

- 图片接口用于封面/缩略图资产，`image add --cover` 会更新物品封面。
- 普通附件接口用于手册、数据表、说明文档等资料，也允许上传普通图片。
- 前端附件列表只隐藏当前封面资产，避免封面图在“附件”区域重复出现；通过附件入口上传的图片仍会作为资料附件展示。

## 写入边界与工作流

- 库存默认不允许为负；创建、更新、入库、出库、调整都会校验。
- 删除物品是归档；归档后禁止库存和位置变更，包括 `move/add/use/adjust`，也包括通用 `PATCH /api/items/{id}` 的 `quantity/unit/location_id/location_text` 字段。
- 关键写接口支持请求体 `request_id` 和请求头 `Idempotency-Key`；重复提交同一键不会重复创建、扣减或绑定。
- 写操作来源字段统一为 `source/module/operator/request_id`，关键动作会写入审计日志。
- `/api/tasks` 提供轻量任务提交、详情和状态查询，状态为 `queued/running/succeeded/failed`。
- `/api/workflows/plans` 提供批量导入、批量出库和 Agent 操作的 plan / confirm。plan 只预览不落库；confirm 基于已保存的 plan 执行，重复 confirm 不重复副作用。
- workflow confirm 失败时会回滚本次业务写入，并记录 failed task，便于排查中途失败。

## 已确认的设计取舍

- ORM 使用 SQLAlchemy 2.x，Schema 使用 Pydantic。
- 数据库结构只通过 Alembic 迁移维护，应用启动不隐式建表。
- 物品编号按分类前缀递增，例如 `FIL-000001`。
- 分类筛选以分类分支为单位；父分类包含所有子孙分类。
- 位置 `code/full_code` 第一版创建后不允许修改。
- 收纳盒格位由容器布局自动生成，格位编号创建后应保持稳定，便于实物贴标。
- 删除物品默认归档；如确认同时删除附件，调用 `DELETE /api/items/{id_or_code}?delete_attachments=true`，并同步释放上传文件和缩略图。
- 归档物品保留查询和备注能力，但不允许库存或位置继续变化。
- 备份恢复前会先创建当前快照。
- 上传文件默认限制 50MB，图片 MIME 限制为 JPEG/PNG/WebP/GIF。
- 搜索条件由 `search_service.fulltext_where()` 统一生成，物品列表和搜索接口共用。
