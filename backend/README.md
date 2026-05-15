# 工坊物栈后端

第一阶段实现后端核心闭环：物品、分类、位置、搜索、备注、图片/附件、备份、API Token，以及完整 CLI 客户端。

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
python -m app.cli.main item notes FIL-000001
python -m app.cli.main item add-note FIL-000001 "打印前建议烘干"

# 分类
python -m app.cli.main category list
python -m app.cli.main category tree
python -m app.cli.main category add "树脂材料" --slug resin --prefix RES
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
python -m app.cli.main image-add FIL-000001 ./pla.jpg --cover
python -m app.cli.main file-add ELE-000001 ./datasheet.pdf
python -m app.cli.main file-list ELE-000001
python -m app.cli.main file-delete 18

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
- 图片上传只接受 JPEG、PNG、WebP、GIF；其他文件请使用 `file-add`。
- `image-add --cover` 会将该图片设置为物品封面。

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
- 搜索结果包含 `matched_by` 标记命中维度

## 已确认的设计取舍

- ORM 使用 SQLAlchemy 2.x，Schema 使用 Pydantic。
- 数据库迁移预留 Alembic。
- 物品编号按分类前缀递增，例如 `FIL-000001`。
- 位置 `code/full_code` 第一版创建后不允许修改。
- 删除物品默认归档；如确认同时删除附件，调用 `DELETE /api/items/{id_or_code}?delete_attachments=true`。
- 备份恢复前会先创建当前快照。
- 上传文件默认限制 50MB，图片 MIME 限制为 JPEG/PNG/WebP/GIF。
- 搜索条件由 `search_service.fulltext_where()` 统一生成，物品列表和搜索接口共用。
