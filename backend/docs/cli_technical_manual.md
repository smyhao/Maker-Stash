# CLI 模块技术手册

## 1. 架构概览

```
用户命令 → Click Group/Command → CliClient.request() → HTTP API → 后端 Service
                                     ↑
                              upload() / download()    文件传输
```

CLI 是 API 的纯客户端，不直连数据库。通过 `httpx` 调用后端 REST API。

### 文件组织

```
app/cli/
├── __init__.py
├── config.py        配置读写（TOML 格式）
├── client.py        HTTP 客户端封装 + JSON 输出
└── main.py          所有 Click 命令定义
```

### 命令入口

通过 `pyproject.toml` 注册为 `stash` 命令：

```toml
[project.scripts]
stash = "app.cli.main:cli"
```

未安装时通过 `python -m app.cli.main` 运行。

---

## 2. CliClient

`app/cli/client.py` 封装了三种 HTTP 操作。

### 2.1 request() — 普通 JSON 请求

```python
def request(
    self,
    method: str,          # GET/POST/PATCH/DELETE
    path: str,            # /api/items
    *,
    params: dict | None,  # 查询参数
    json_body: dict | None, # JSON 请求体
) -> dict[str, Any]:     # 返回 data 部分
```

自动添加 `Authorization: Bearer <token>` 头。自动解析 API 响应，失败时抛出 `click.ClickException`。

**使用示例：**

```python
client = CliClient()
data = client.request("GET", "/api/items", params={"q": "PLA", "page_size": 10})
data = client.request("POST", "/api/items", json_body={"name": "测试"})
data = client.request("DELETE", f"/api/items/{code}")
```

### 2.2 upload() — 文件上传

```python
def upload(
    self,
    path: str,            # /api/items/{code}/images
    file_path: Path,      # 本地文件路径
    *,
    extra_fields: dict | None,  # 额外表单字段（如 is_cover）
) -> dict[str, Any]:
```

使用 `multipart/form-data` 上传文件。

**使用示例：**

```python
client = CliClient()
data = client.upload(f"/api/items/{code}/images", Path("./photo.jpg"), extra_fields={"is_cover": "true"})
```

### 2.3 download() — 文件下载

```python
def download(self, path: str, output: Path) -> None:
```

下载文件到本地路径。

**使用示例：**

```python
client = CliClient()
client.download(f"/api/backups/{backup_id}/download", Path("backup.zip"))
```

### 2.4 错误处理

所有方法在 API 返回失败时自动抛出 `click.ClickException`，格式为 `"ERROR_CODE: message"`。命令函数不需要手动处理 API 错误。

---

## 3. Config 管理

`app/cli/config.py` 管理 CLI 配置，存储在 `~/.workshop-stash/config.toml`。

### 配置项

| Key | 说明 | 默认值 |
|---|---|---|
| `api_url` | 后端 API 地址 | `http://127.0.0.1:8000` |
| `token` | API Token | 空 |

首次 Token 需要在后端创建：

```bash
python -m app.scripts.create_token --name cli
stash config set token <token>
```

脚本输出的明文 Token 只显示一次；丢失后需要重新创建。CLI 会把 Token 写入 `~/.workshop-stash/config.toml`，后续请求自动添加 `Authorization: Bearer <token>`。

### 函数

```python
load_config(path=None) -> dict[str, str]   # 加载配置
save_config(config, path=None) -> None     # 保存配置
mask_token(token: str | None) -> str       # 掩码显示 Token
config_path() -> Path                      # 配置文件路径
```

---

## 4. 命令编写规范

### 命令结构

所有命令采用 `stash <resource> <action>` 格式：

```python
@cli.group()
def item() -> None:
    """管理物品。"""

@item.command("list")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_list(as_json: bool) -> None:
    ...
```

### --json 支持

查询类命令必须支持 `--json` 输出，使用 `echo_json()` 函数：

```python
@click.option("--json-output", "--json", "as_json", is_flag=True)
def some_list_command(as_json: bool) -> None:
    data = CliClient().request("GET", "/api/xxx")
    if as_json:
        echo_json(data)
        return
    # 人类可读格式
    for row in data.get("items", []):
        click.echo(f"{row['code']:<12} {row['name']}")
```

`echo_json()` 输出格式化 JSON，`ensure_ascii=False` 保证中文正常显示。

### 典型命令模式

**查询列表：**

```python
@item.command("list")
@click.option("--category")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_list(category: str | None, as_json: bool) -> None:
    params = {"category": category}
    data = CliClient().request("GET", "/api/items", params={k: v for k, v in params.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    for row in data.get("items", []):
        click.echo(f"{row['code']:<12} {row['name']}")
```

**查看详情：**

```python
@item.command("show")
@click.argument("id_or_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_show(id_or_code: str, as_json: bool) -> None:
    data = CliClient().request("GET", f"/api/items/{id_or_code}")
    if as_json:
        echo_json(data)
        return
    click.echo(f"编号: {data['code']}")
    click.echo(f"名称: {data['name']}")
```

**新增资源：**

```python
@category.command("add")
@click.argument("name")
@click.option("--slug", required=True)
@click.option("--prefix", "code_prefix", required=True)
@click.option("--json-output", "--json", "as_json", is_flag=True)
def category_add(name: str, slug: str, code_prefix: str, as_json: bool) -> None:
    data = CliClient().request("POST", "/api/categories",
        json_body={"name": name, "slug": slug, "code_prefix": code_prefix})
    if as_json:
        echo_json(data)
        return
    click.echo(f"已新增分类 {data['id']} {data['name']}")
```

**执行动作：**

```python
@item.command("move")
@click.argument("id_or_code")
@click.option("--to", "location_code")
@click.option("--to-text", "location_text")
def item_move(id_or_code: str, location_code: str | None, location_text: str | None) -> None:
    if not location_code and not location_text:
        raise click.ClickException("必须提供 --to 或 --to-text")
    data = CliClient().request("POST", f"/api/items/{id_or_code}/move",
        json_body={"location_code": location_code, "location_text": location_text, "source": "cli"})
    click.echo(f"已移动 {data['code']}")
```

**删除资源：**

```python
@tag.command("delete")
@click.argument("tag_id", type=int)
def tag_delete(tag_id: int) -> None:
    CliClient().request("DELETE", f"/api/tags/{tag_id}")
    click.echo(f"已删除标签 {tag_id}")
```

---

## 5. 全部命令清单

### 5.1 config — 配置管理

| 命令 | 说明 |
|---|---|
| `stash config set <key> <value>` | 设置 api_url 或 token |
| `stash config get <key>` | 查看配置值 |
| `stash config show` | 显示全部配置 |

### 5.2 ping / system — 系统操作

| 命令 | 说明 |
|---|---|
| `stash ping` | 测试 API 连通性 |
| `stash system info` | 显示系统版本、物品数量、Token 状态、最近备份 |

### 5.3 search — 搜索

```bash
stash search <query> [--category X] [--location X] [--tag X] [--limit N] [--json]
```

结果默认显示编号、名称、数量、状态和 `matched_by` 标记。

### 5.4 item — 物品管理

| 命令 | 参数/选项 | 说明 |
|---|---|---|
| `item list` | `--category --location --tag --status --restock --favorite --json` | 物品列表 |
| `item show` | `<id_or_code> --json` | 查看详情 |
| `item add` | `--name --category --location --location-text --quantity --unit --status --description --note --tag(可多次) --attr key=value(可多次) --json` | 新增物品 |
| `item update` | `<id_or_code> --name --status --description --unit --json` | 修改物品 |
| `item delete` | `<id_or_code> --force --json` | 归档物品（`--force` 同时删附件） |
| `item move` | `<id_or_code> --to --to-text --note --json` | 移动位置 |
| `item add-qty` | `<id_or_code> --amount --unit --note --json` | 入库 |
| `item use` | `<id_or_code> --amount --unit --note --json` | 使用/出库 |
| `item adjust` | `<id_or_code> --quantity --unit --note --json` | 直接调整数量 |
| `item restock` | `<id_or_code>` | 标记需要补货 |
| `item unstock` | `<id_or_code>` | 取消补货标记 |
| `item favorite` | `<id_or_code>` | 标记常用 |
| `item unfavorite` | `<id_or_code>` | 取消常用 |
| `item tag` | `<id_or_code> <tags...>` | 添加标签 |
| `item untag` | `<id_or_code> <tag>` | 移除标签 |
| `item alias` | `<id_or_code> <alias>` | 添加别名 |
| `item unalias` | `<id_or_code> <alias>` | 移除别名 |
| `item bind` | `<id_or_code> --type --value --description` | 绑定外部标识 |
| `item unbind` | `<id_or_code> <identifier_id>` | 解绑外部标识 |
| `item find-id` | `<identifier> --json` | 按外部标识查找物品 |
| `note list` | `<id_or_code> --json` | 查看备注列表 |
| `note add` | `<id_or_code> <content> --type --source` | 添加备注 |

### 5.5 category — 分类管理

| 命令 | 参数/选项 | 说明 |
|---|---|---|
| `category list` | `--json` | 分类平铺列表 |
| `category tree` | `--json` | 分类树形结构 |
| `category add` | `<name> --slug --prefix [--parent-id] [--description] --json` | 新增分类 |
| `category update` | `<id> --name --prefix --description --json` | 修改分类 |
| `category delete` | `<id>` | 删除分类 |

### 5.6 location — 位置管理

| 命令 | 参数/选项 | 说明 |
|---|---|---|
| `location list` | `--json` | 位置平铺列表 |
| `location tree` | `--json` | 位置树形结构 |
| `location show` | `<id_or_code> --json` | 查看位置详情（ID 或 full_code） |
| `location add` | `<name> --code [--parent] [--type] [--description] --json` | 新增位置 |
| `location update` | `<id> --name --type --description --json` | 修改位置 |
| `location delete` | `<id>` | 删除位置 |
| `location items` | `<full_code> --json` | 查看某位置下物品 |

### 5.7 tag — 标签管理

| 命令 | 参数/选项 | 说明 |
|---|---|---|
| `tag list` | `--json` | 标签列表 |
| `tag add` | `<name> [--slug]` | 新增标签 |
| `tag delete` | `<tag_id>` | 删除标签 |

### 5.8 attr-def — 属性模板管理

| 命令 | 参数/选项 | 说明 |
|---|---|---|
| `attr-def list` | `[--category-id] --json` | 属性模板列表 |
| `attr-def add` | `--category-id --name --key [--type] [--unit] [--required]` | 新增属性模板 |
| `attr-def update` | `<id> --name --unit --required --json` | 修改属性模板 |
| `attr-def delete` | `<id>` | 删除属性模板 |

### 5.9 image / file — 图片和附件

| 命令 | 参数/选项 | 说明 |
|---|---|---|
| `image add` | `<id_or_code> <file> [--cover]` | 上传图片 |
| `file add` | `<id_or_code> <file>` | 上传附件 |
| `file list` | `<id_or_code> --json` | 附件列表 |
| `file delete` | `<attachment_id>` | 删除附件 |

旧版 `image-add`、`file-add`、`file-list`、`file-delete` 仍作为隐藏兼容命令保留；新文档和脚本应使用 `stash <resource> <action>` 形式。

限制与约定：

- 单个上传文件默认最大 50MB，限制来自后端 `max_upload_bytes`。
- `image add` 只支持 JPEG、PNG、WebP、GIF；其他文件使用 `file add`。
- `image add --cover` 会将上传图片设置为物品封面。

### 5.10 backup — 备份管理

| 命令 | 参数/选项 | 说明 |
|---|---|---|
| `backup create` | `[--note] [--without-uploads] --json` | 创建备份 |
| `backup list` | `--json` | 备份列表 |
| `backup restore` | `<backup_id> --json` | 恢复备份 |
| `backup download` | `<backup_id> [--output]` | 下载备份文件 |

恢复注意事项：

- `backup create` 默认包含上传文件；`--without-uploads` 只备份数据库。
- `backup restore` 执行前后端会自动创建当前快照。
- 恢复会覆盖当前数据库和上传文件目录，建议先执行 `backup download` 保存一份离线备份。
- 如后端返回 `BACKUP_IN_PROGRESS`，说明已有备份或恢复任务在执行，稍后重试。

---

## 6. 辅助函数

### echo_json

```python
def echo_json(data: Any) -> None:
    click.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))
```

- `ensure_ascii=False` 保证中文正常输出
- `default=str` 处理 datetime/Decimal 等类型
- 所有查询类命令的 `--json` 统一调用此函数

### _fmt_qty

```python
def _fmt_qty(quantity: str | None, unit: str | None) -> str:
    if quantity is None:
        return ""
    return f"{quantity} {unit or ''}".strip()
```

格式化数量+单位显示。

### _echo_location_node / _echo_tree_node

递归输出树形结构，用缩进表示层级。

### _parse_attr

解析 `--attr key=value` 格式的命令行参数。

---

## 7. 新增命令 Checklist

1. **确定 API** — 先确认后端已有对应接口
2. **添加命令函数** — 在 `main.py` 对应 group 下添加
3. **遵循命名** — 资源名单数，动作用 list/show/add/update/delete
4. **支持 --json** — 查询类命令加 `--json-output` 选项
5. **传 source** — 修改类操作 json_body 中加 `"source": "cli"`
6. **过滤空参数** — 用 `{k: v for k, v in params.items() if v is not None}` 过滤
7. **测试** — 在 `tests/test_cli_commands.py` 验证 help 输出包含新命令
8. **文档** — 更新本手册和 `backend/README.md`
