from decimal import Decimal
from pathlib import Path

import click

from app.cli.client import CliClient, echo_json
from app.cli.config import load_config, mask_token, save_config


@click.group()
def cli() -> None:
    """工坊物栈命令行客户端。"""


# ── config ──────────────────────────────────────────────────────────────


@cli.group()
def config() -> None:
    """管理 CLI 配置。"""


@config.command("set")
@click.argument("key", type=click.Choice(["api_url", "token"]))
@click.argument("value")
def config_set(key: str, value: str) -> None:
    current = load_config()
    current[key] = value
    save_config(current)
    click.echo(f"已设置 {key}")


@config.command("get")
@click.argument("key", type=click.Choice(["api_url", "token"]))
def config_get(key: str) -> None:
    current = load_config()
    value = current.get(key, "")
    click.echo(mask_token(value) if key == "token" else value)


@config.command("show")
def config_show() -> None:
    current = load_config()
    click.echo(f"api_url = {current.get('api_url', '')}")
    click.echo(f"token = {mask_token(current.get('token'))}")


# ── ping / system ───────────────────────────────────────────────────────


@cli.command()
def ping() -> None:
    data = CliClient().request("GET", "/api/health")
    click.echo(data.get("status", "ok"))


@cli.group("system")
def system() -> None:
    """查看系统信息。"""


@system.command("info")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def system_info(as_json: bool) -> None:
    data = CliClient().request("GET", "/api/system/info")
    if as_json:
        echo_json(data)
        return
    click.echo(f"名称:     {data.get('name')}")
    click.echo(f"版本:     {data.get('version')}")
    click.echo(f"环境:     {data.get('environment')}")
    counts = data.get("counts", {})
    click.echo(f"物品数:   {counts.get('items', 0)}")
    click.echo(f"分类数:   {counts.get('categories', 0)}")
    click.echo(f"位置数:   {counts.get('locations', 0)}")
    auth = data.get("auth", {})
    click.echo(f"Token:    {'启用' if auth.get('api_token_enabled') else '关闭'}")
    click.echo(f"最近备份: {data.get('latest_backup') or '无'}")


# ── search ──────────────────────────────────────────────────────────────


@cli.command()
@click.argument("query")
@click.option("--category")
@click.option("--location")
@click.option("--tag")
@click.option("--limit", type=int, default=20)
@click.option("--json-output", "--json", "as_json", is_flag=True)
def search(
    query: str,
    category: str | None,
    location: str | None,
    tag: str | None,
    limit: int,
    as_json: bool,
) -> None:
    params: dict = {"q": query, "limit": limit}
    if category:
        params["category"] = category
    if location:
        params["location"] = location
    if tag:
        params["tag"] = tag
    data = CliClient().request("GET", "/api/search", params=params)
    if as_json:
        echo_json(data)
        return
    for item in data.get("items", []):
        quantity = _fmt_qty(item.get("quantity"), item.get("unit"))
        matched = ",".join(item.get("matched_by", []))
        click.echo(f"{item['code']:<12} {item['name']:<24} {quantity:<12} [{matched}]")


# ── item ────────────────────────────────────────────────────────────────


@cli.group()
def item() -> None:
    """管理物品。"""


@item.command("list")
@click.option("--category")
@click.option("--location")
@click.option("--tag")
@click.option("--status")
@click.option("--restock", is_flag=True)
@click.option("--favorite", is_flag=True)
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_list(
    category: str | None,
    location: str | None,
    tag: str | None,
    status: str | None,
    restock: bool,
    favorite: bool,
    as_json: bool,
) -> None:
    params = {
        "category": category,
        "location": location,
        "tag": tag,
        "status": status,
        "need_restock": True if restock else None,
        "favorite": True if favorite else None,
    }
    data = CliClient().request("GET", "/api/items", params={k: v for k, v in params.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    for row in data.get("items", []):
        quantity = _fmt_qty(row.get("quantity"), row.get("unit"))
        click.echo(f"{row['code']:<12} {row['name']:<24} {quantity:<12} {row['status']}")


@item.command("show")
@click.argument("id_or_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_show(id_or_code: str, as_json: bool) -> None:
    data = CliClient().request("GET", f"/api/items/{id_or_code}")
    if as_json:
        echo_json(data)
        return
    click.echo(f"编号:   {data['code']}")
    click.echo(f"名称:   {data['name']}")
    click.echo(f"状态:   {data['status']}")
    click.echo(f"数量:   {_fmt_qty(data.get('quantity'), data.get('unit'))}")
    click.echo(f"位置:   {data.get('location_text') or ''}")
    if data.get("description"):
        click.echo(f"备注:   {data['description']}")
    if data.get("need_restock"):
        click.echo("标记:   需要补货")
    if data.get("is_favorite"):
        click.echo("标记:   常用")


@item.command("add")
@click.option("--name", required=True)
@click.option("--category")
@click.option("--location", "location_code")
@click.option("--location-text")
@click.option("--quantity", type=Decimal)
@click.option("--unit")
@click.option("--status", default="normal")
@click.option("--description")
@click.option("--note")
@click.option("--tag", "tags", multiple=True)
@click.option("--attr", "attrs", multiple=True, help="属性 key=value")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_add(
    name: str,
    category: str | None,
    location_code: str | None,
    location_text: str | None,
    quantity: Decimal | None,
    unit: str | None,
    status: str,
    description: str | None,
    note: str | None,
    tags: tuple[str, ...],
    attrs: tuple[str, ...],
    as_json: bool,
) -> None:
    body: dict = {
        "name": name,
        "category": category,
        "location_code": location_code,
        "location_text": location_text,
        "quantity": str(quantity) if quantity is not None else None,
        "unit": unit,
        "status": status,
        "description": description,
        "note": note,
    }
    if tags:
        body["tags"] = list(tags)
    if attrs:
        body["attributes"] = [_parse_attr(a) for a in attrs]
    data = CliClient().request("POST", "/api/items", json_body={k: v for k, v in body.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    click.echo(f"已新增 {data['code']}  {data['name']}")


@item.command("update")
@click.argument("id_or_code")
@click.option("--name")
@click.option("--status")
@click.option("--description")
@click.option("--unit")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_update(
    id_or_code: str,
    name: str | None,
    status: str | None,
    description: str | None,
    unit: str | None,
    as_json: bool,
) -> None:
    body = {"name": name, "status": status, "description": description, "unit": unit}
    data = CliClient().request("PATCH", f"/api/items/{id_or_code}", json_body={k: v for k, v in body.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    click.echo(f"已更新 {data['code']}  {data['name']}")


@item.command("delete")
@click.argument("id_or_code")
@click.option("--force", is_flag=True, help="同时删除附件")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_delete(id_or_code: str, force: bool, as_json: bool) -> None:
    params = {"delete_attachments": "true"} if force else None
    data = CliClient().request("DELETE", f"/api/items/{id_or_code}", params=params)
    if as_json:
        echo_json(data)
        return
    click.echo(f"已归档 {id_or_code}")


@item.command("move")
@click.argument("id_or_code")
@click.option("--to", "location_code")
@click.option("--to-text", "location_text")
@click.option("--note")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_move(
    id_or_code: str,
    location_code: str | None,
    location_text: str | None,
    note: str | None,
    as_json: bool,
) -> None:
    if not location_code and not location_text:
        raise click.ClickException("必须提供 --to 或 --to-text")
    data = CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/move",
        json_body={"location_code": location_code, "location_text": location_text, "note": note, "source": "cli"},
    )
    if as_json:
        echo_json(data)
        return
    click.echo(f"已移动 {data['code']}  {data['name']}")


@item.command("add-qty")
@click.argument("id_or_code")
@click.option("--amount", required=True, type=Decimal)
@click.option("--unit")
@click.option("--note")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_add_qty(id_or_code: str, amount: Decimal, unit: str | None, note: str | None, as_json: bool) -> None:
    data = _qty_action(id_or_code, "add", amount, unit, note)
    if as_json:
        echo_json(data)
        return
    click.echo(f"当前数量: {_fmt_qty(data.get('quantity'), data.get('unit'))}")


@item.command("use")
@click.argument("id_or_code")
@click.option("--amount", required=True, type=Decimal)
@click.option("--unit")
@click.option("--note")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_use(id_or_code: str, amount: Decimal, unit: str | None, note: str | None, as_json: bool) -> None:
    data = _qty_action(id_or_code, "use", amount, unit, note)
    if as_json:
        echo_json(data)
        return
    click.echo(f"当前数量: {_fmt_qty(data.get('quantity'), data.get('unit'))}")


@item.command("adjust")
@click.argument("id_or_code")
@click.option("--quantity", required=True, type=Decimal)
@click.option("--unit")
@click.option("--note")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_adjust(id_or_code: str, quantity: Decimal, unit: str | None, note: str | None, as_json: bool) -> None:
    data = CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/adjust",
        json_body={"quantity": str(quantity), "unit": unit, "note": note, "source": "cli"},
    )
    if as_json:
        echo_json(data)
        return
    click.echo(f"当前数量: {_fmt_qty(data.get('quantity'), data.get('unit'))}")


@item.command("restock")
@click.argument("id_or_code")
def item_restock(id_or_code: str) -> None:
    data = CliClient().request("POST", f"/api/items/{id_or_code}/mark-restock")
    click.echo(f"已标记补货 {data['code']}")


@item.command("unstock")
@click.argument("id_or_code")
def item_unstock(id_or_code: str) -> None:
    data = CliClient().request("POST", f"/api/items/{id_or_code}/unmark-restock")
    click.echo(f"已取消补货 {data['code']}")


@item.command("favorite")
@click.argument("id_or_code")
def item_favorite(id_or_code: str) -> None:
    data = CliClient().request("POST", f"/api/items/{id_or_code}/favorite")
    click.echo(f"已标记常用 {data['code']}")


@item.command("unfavorite")
@click.argument("id_or_code")
def item_unfavorite(id_or_code: str) -> None:
    data = CliClient().request("POST", f"/api/items/{id_or_code}/unfavorite")
    click.echo(f"已取消常用 {data['code']}")


@item.command("tag")
@click.argument("id_or_code")
@click.argument("tags", nargs=-1, required=True)
def item_tag(id_or_code: str, tags: tuple[str, ...]) -> None:
    data = CliClient().request("POST", f"/api/items/{id_or_code}/tags", json_body={"tags": list(tags)})
    names = ", ".join(tag["name"] for tag in data.get("tags", []))
    click.echo(f"已添加标签: {names}")


@item.command("untag")
@click.argument("id_or_code")
@click.argument("tag")
def item_untag(id_or_code: str, tag: str) -> None:
    CliClient().request("DELETE", f"/api/items/{id_or_code}/tags/{tag}")
    click.echo(f"已移除标签 {tag}")


@item.command("alias")
@click.argument("id_or_code")
@click.argument("alias_value")
def item_alias(id_or_code: str, alias_value: str) -> None:
    data = CliClient().request("POST", f"/api/items/{id_or_code}/aliases", json_body={"alias": alias_value})
    click.echo(f"已添加别名 {data['alias']}")


@item.command("unalias")
@click.argument("id_or_code")
@click.argument("alias_value")
def item_unalias(id_or_code: str, alias_value: str) -> None:
    CliClient().request("DELETE", f"/api/items/{id_or_code}/aliases/{alias_value}")
    click.echo(f"已移除别名 {alias_value}")


@item.command("bind")
@click.argument("id_or_code")
@click.option("--type", "identifier_type", required=True)
@click.option("--value", required=True)
@click.option("--description")
def item_bind(id_or_code: str, identifier_type: str, value: str, description: str | None) -> None:
    data = CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/identifiers",
        json_body={"type": identifier_type, "value": value, "description": description},
    )
    click.echo(f"已绑定 {data['type']}:{data['value']}")


@item.command("unbind")
@click.argument("id_or_code")
@click.argument("identifier_id", type=int)
def item_unbind(id_or_code: str, identifier_id: int) -> None:
    CliClient().request("DELETE", f"/api/items/{id_or_code}/identifiers/{identifier_id}")
    click.echo(f"已解绑标识 {identifier_id}")


@item.command("find-id")
@click.argument("identifier")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_find_id(identifier: str, as_json: bool) -> None:
    data = CliClient().request("GET", f"/api/items/by-identifier/{identifier}")
    if as_json:
        echo_json(data)
        return
    click.echo(f"{data['code']}  {data['name']}")


@item.command("notes")
@click.argument("id_or_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_notes(id_or_code: str, as_json: bool) -> None:
    data = CliClient().request("GET", f"/api/items/{id_or_code}/notes")
    if as_json:
        echo_json(data)
        return
    for note in data.get("notes", []):
        tag = note.get("note_type", "note")
        content = note.get("content", "")
        time = note.get("created_at", "")
        click.echo(f"  [{tag}] {content}  ({time})")


@item.command("add-note")
@click.argument("id_or_code")
@click.argument("content")
@click.option("--type", "note_type", default="note")
@click.option("--source", default="cli")
def item_add_note(id_or_code: str, content: str, note_type: str, source: str) -> None:
    data = CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/notes",
        json_body={"note_type": note_type, "content": content, "source": source},
    )
    click.echo(f"已添加备注 {data.get('id')}")


# ── image / file / note ─────────────────────────────────────────────────


@cli.group()
def image() -> None:
    """管理物品图片。"""


@image.command("add")
@click.argument("id_or_code")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--cover", is_flag=True)
def image_add(id_or_code: str, file: Path, cover: bool) -> None:
    extra = {"is_cover": "true"} if cover else None
    data = CliClient().upload(f"/api/items/{id_or_code}/images", file, extra_fields=extra)
    click.echo(f"已上传图片 {data.get('original_name')}")


@cli.command("image-add", hidden=True)
@click.argument("id_or_code")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--cover", is_flag=True)
def image_add_legacy(id_or_code: str, file: Path, cover: bool) -> None:
    image_add.callback(id_or_code, file, cover)  # type: ignore[attr-defined]


@cli.group("file")
def file_group() -> None:
    """管理物品附件。"""


@file_group.command("add")
@click.argument("id_or_code")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def file_add(id_or_code: str, file: Path) -> None:
    data = CliClient().upload(f"/api/items/{id_or_code}/attachments", file)
    click.echo(f"已上传附件 {data.get('original_name')}")


@file_group.command("list")
@click.argument("id_or_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def file_list(id_or_code: str, as_json: bool) -> None:
    data = CliClient().request("GET", f"/api/items/{id_or_code}/attachments")
    if as_json:
        echo_json(data)
        return
    for a in data.get("attachments", []):
        size = a.get("size_bytes") or 0
        click.echo(f"  {a['id']:<6} {a['attachment_type']:<10} {a['original_name']:<30} {size} bytes")


@file_group.command("delete")
@click.argument("attachment_id", type=int)
def file_delete(attachment_id: int) -> None:
    CliClient().request("DELETE", f"/api/attachments/{attachment_id}")
    click.echo(f"已删除附件 {attachment_id}")


@cli.command("file-add", hidden=True)
@click.argument("id_or_code")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def file_add_legacy(id_or_code: str, file: Path) -> None:
    file_add.callback(id_or_code, file)  # type: ignore[attr-defined]


@cli.command("file-list", hidden=True)
@click.argument("id_or_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def file_list_legacy(id_or_code: str, as_json: bool) -> None:
    file_list.callback(id_or_code, as_json)  # type: ignore[attr-defined]


@cli.command("file-delete", hidden=True)
@click.argument("attachment_id", type=int)
def file_delete_legacy(attachment_id: int) -> None:
    file_delete.callback(attachment_id)  # type: ignore[attr-defined]


@cli.group()
def note() -> None:
    """管理物品备注。"""


@note.command("list")
@click.argument("id_or_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def note_list(id_or_code: str, as_json: bool) -> None:
    item_notes.callback(id_or_code, as_json)  # type: ignore[attr-defined]


@note.command("add")
@click.argument("id_or_code")
@click.argument("content")
@click.option("--type", "note_type", default="note")
@click.option("--source", default="cli")
def note_add(id_or_code: str, content: str, note_type: str, source: str) -> None:
    item_add_note.callback(id_or_code, content, note_type, source)  # type: ignore[attr-defined]


# ── tag ─────────────────────────────────────────────────────────────────


@cli.group()
def tag() -> None:
    """管理标签。"""


@tag.command("list")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def tag_list(as_json: bool) -> None:
    data = CliClient().request("GET", "/api/tags")
    if as_json:
        echo_json(data)
        return
    for row in data.get("tags", []):
        click.echo(f"  {row['id']:<6} {row['name']}")


@tag.command("add")
@click.argument("name")
@click.option("--slug")
def tag_add(name: str, slug: str | None) -> None:
    data = CliClient().request("POST", "/api/tags", json_body={"name": name, "slug": slug})
    click.echo(f"已新增标签 {data['name']}")


@tag.command("delete")
@click.argument("tag_id", type=int)
def tag_delete(tag_id: int) -> None:
    CliClient().request("DELETE", f"/api/tags/{tag_id}")
    click.echo(f"已删除标签 {tag_id}")


# ── category ────────────────────────────────────────────────────────────


@cli.group()
def category() -> None:
    """管理分类。"""


@category.command("list")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def category_list(as_json: bool) -> None:
    data = CliClient().request("GET", "/api/categories")
    if as_json:
        echo_json(data)
        return
    for row in data.get("categories", []):
        prefix = row.get("code_prefix", "")
        click.echo(f"  {row['id']:<6} {prefix:<8} {row['name']}")


@category.command("tree")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def category_tree(as_json: bool) -> None:
    data = CliClient().request("GET", "/api/categories/tree")
    if as_json:
        echo_json(data)
        return
    for node in data.get("categories", []):
        _echo_tree_node(node)


@category.command("add")
@click.argument("name")
@click.option("--slug", required=True)
@click.option("--prefix", "code_prefix", required=True)
@click.option("--parent-id", type=int)
@click.option("--description")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def category_add(
    name: str,
    slug: str,
    code_prefix: str,
    parent_id: int | None,
    description: str | None,
    as_json: bool,
) -> None:
    body: dict = {"name": name, "slug": slug, "code_prefix": code_prefix, "description": description}
    if parent_id:
        body["parent_id"] = parent_id
    data = CliClient().request("POST", "/api/categories", json_body={k: v for k, v in body.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    click.echo(f"已新增分类 {data['id']} {data['name']}")


@category.command("update")
@click.argument("category_id", type=int)
@click.option("--name")
@click.option("--prefix", "code_prefix")
@click.option("--description")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def category_update(
    category_id: int,
    name: str | None,
    code_prefix: str | None,
    description: str | None,
    as_json: bool,
) -> None:
    body = {"name": name, "code_prefix": code_prefix, "description": description}
    data = CliClient().request("PATCH", f"/api/categories/{category_id}", json_body={k: v for k, v in body.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    click.echo(f"已更新分类 {data['id']} {data['name']}")


@category.command("delete")
@click.argument("category_id", type=int)
def category_delete(category_id: int) -> None:
    CliClient().request("DELETE", f"/api/categories/{category_id}")
    click.echo(f"已删除分类 {category_id}")


# ── location ────────────────────────────────────────────────────────────


@cli.group()
def location() -> None:
    """管理位置。"""


@location.command("list")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def location_list(as_json: bool) -> None:
    data = CliClient().request("GET", "/api/locations")
    if as_json:
        echo_json(data)
        return
    for row in data.get("locations", []):
        click.echo(f"{row['full_code']:<28} {row['name']}")


@location.command("tree")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def location_tree(as_json: bool) -> None:
    data = CliClient().request("GET", "/api/locations/tree")
    if as_json:
        echo_json(data)
        return
    for row in data.get("locations", []):
        _echo_location_node(row)


@location.command("show")
@click.argument("id_or_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def location_show(id_or_code: str, as_json: bool) -> None:
    if id_or_code.isdigit():
        data = CliClient().request("GET", f"/api/locations/{id_or_code}")
    else:
        data = CliClient().request("GET", f"/api/locations/by-code/{id_or_code}")
    if as_json:
        echo_json(data)
        return
    click.echo(f"编号:   {data['full_code']}")
    click.echo(f"名称:   {data['name']}")
    click.echo(f"类型:   {data.get('type') or '未指定'}")
    if data.get("description"):
        click.echo(f"说明:   {data['description']}")


@location.command("add")
@click.argument("name")
@click.option("--code", required=True)
@click.option("--parent")
@click.option("--type", "location_type")
@click.option("--description")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def location_add(
    name: str,
    code: str,
    parent: str | None,
    location_type: str | None,
    description: str | None,
    as_json: bool,
) -> None:
    data = CliClient().request(
        "POST",
        "/api/locations",
        json_body={"name": name, "code": code, "parent_code": parent, "type": location_type, "description": description},
    )
    if as_json:
        echo_json(data)
        return
    click.echo(f"已新增位置 {data['full_code']}  {data['name']}")


@location.command("update")
@click.argument("location_id", type=int)
@click.option("--name")
@click.option("--type", "location_type")
@click.option("--description")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def location_update(
    location_id: int,
    name: str | None,
    location_type: str | None,
    description: str | None,
    as_json: bool,
) -> None:
    body = {"name": name, "type": location_type, "description": description}
    data = CliClient().request("PATCH", f"/api/locations/{location_id}", json_body={k: v for k, v in body.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    click.echo(f"已更新位置 {data['full_code']}  {data['name']}")


@location.command("delete")
@click.argument("location_id", type=int)
def location_delete(location_id: int) -> None:
    CliClient().request("DELETE", f"/api/locations/{location_id}")
    click.echo(f"已删除位置 {location_id}")


@location.command("items")
@click.argument("full_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def location_items(full_code: str, as_json: bool) -> None:
    data = CliClient().request("GET", f"/api/locations/by-code/{full_code}/items")
    if as_json:
        echo_json(data)
        return
    for row in data.get("items", []):
        quantity = _fmt_qty(row.get("quantity"), row.get("unit"))
        click.echo(f"{row['code']:<12} {row['name']:<24} {quantity:<12} {row['status']}")


# ── attr-def ────────────────────────────────────────────────────────────


@cli.group("attr-def")
def attr_def() -> None:
    """管理属性模板。"""


@attr_def.command("list")
@click.option("--category-id", type=int)
@click.option("--json-output", "--json", "as_json", is_flag=True)
def attr_def_list(category_id: int | None, as_json: bool) -> None:
    params = {"category_id": category_id} if category_id else None
    data = CliClient().request("GET", "/api/attribute-definitions", params=params)
    if as_json:
        echo_json(data)
        return
    for row in data.get("attribute_definitions", []):
        click.echo(f"{row['id']:<6} {row['key']:<20} {row['name']:<20} {row['field_type']}")


@attr_def.command("add")
@click.option("--category-id", required=True, type=int)
@click.option("--name", required=True)
@click.option("--key", required=True)
@click.option("--type", "field_type", default="text")
@click.option("--unit")
@click.option("--required", "is_required", is_flag=True)
def attr_def_add(
    category_id: int,
    name: str,
    key: str,
    field_type: str,
    unit: str | None,
    is_required: bool,
) -> None:
    data = CliClient().request(
        "POST",
        "/api/attribute-definitions",
        json_body={
            "category_id": category_id,
            "name": name,
            "key": key,
            "field_type": field_type,
            "unit": unit,
            "required": is_required,
        },
    )
    click.echo(f"已新增属性模板 {data['id']} {data['key']}")


@attr_def.command("update")
@click.argument("definition_id", type=int)
@click.option("--name")
@click.option("--unit")
@click.option("--required", "is_required", type=bool)
@click.option("--json-output", "--json", "as_json", is_flag=True)
def attr_def_update(
    definition_id: int,
    name: str | None,
    unit: str | None,
    is_required: bool | None,
    as_json: bool,
) -> None:
    body: dict = {"name": name, "unit": unit}
    if is_required is not None:
        body["required"] = is_required
    data = CliClient().request(
        "PATCH",
        f"/api/attribute-definitions/{definition_id}",
        json_body={k: v for k, v in body.items() if v is not None},
    )
    if as_json:
        echo_json(data)
        return
    click.echo(f"已更新属性模板 {data['id']} {data['key']}")


@attr_def.command("delete")
@click.argument("definition_id", type=int)
def attr_def_delete(definition_id: int) -> None:
    CliClient().request("DELETE", f"/api/attribute-definitions/{definition_id}")
    click.echo(f"已删除属性模板 {definition_id}")


# ── backup ──────────────────────────────────────────────────────────────


@cli.group()
def backup() -> None:
    """管理备份。"""


@backup.command("create")
@click.option("--note")
@click.option("--without-uploads", is_flag=True)
@click.option("--json-output", "--json", "as_json", is_flag=True)
def backup_create(note: str | None, without_uploads: bool, as_json: bool) -> None:
    data = CliClient().request(
        "POST",
        "/api/backups",
        json_body={"include_uploads": not without_uploads, "note": note},
    )
    if as_json:
        echo_json(data)
        return
    click.echo(f"已创建备份 {data['backup_id']}")


@backup.command("list")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def backup_list(as_json: bool) -> None:
    data = CliClient().request("GET", "/api/backups")
    if as_json:
        echo_json(data)
        return
    for row in data.get("backups", []):
        click.echo(f"{row['backup_id']:<28} {row['status']:<8} {row.get('size_bytes') or 0} bytes")


@backup.command("restore")
@click.argument("backup_id")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def backup_restore(backup_id: str, as_json: bool) -> None:
    data = CliClient().request("POST", f"/api/backups/{backup_id}/restore")
    if as_json:
        echo_json(data)
        return
    click.echo(f"已恢复备份 {data['backup_id']}")


@backup.command("download")
@click.argument("backup_id")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path))
def backup_download(backup_id: str, output: Path | None) -> None:
    target = output or Path(f"{backup_id}.zip")
    CliClient().download(f"/api/backups/{backup_id}/download", target)
    click.echo(f"已下载到 {target}")


# ── helpers ─────────────────────────────────────────────────────────────


def _qty_action(
    id_or_code: str,
    action: str,
    amount: Decimal,
    unit: str | None,
    note: str | None,
) -> dict:
    return CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/{action}",
        json_body={"amount": str(amount), "unit": unit, "note": note, "source": "cli"},
    )


def _echo_location_node(row: dict, depth: int = 0) -> None:
    click.echo(f"{'  ' * depth}{row['code']}  {row['name']}")
    for child in row.get("children", []):
        _echo_location_node(child, depth + 1)


def _echo_tree_node(node: dict, depth: int = 0) -> None:
    prefix = node.get("code_prefix", "")
    click.echo(f"{'  ' * depth}{node['name']:<12} {prefix}")
    for child in node.get("children", []):
        _echo_tree_node(child, depth + 1)


def _fmt_qty(quantity: str | None, unit: str | None) -> str:
    if quantity is None:
        return ""
    return f"{quantity} {unit or ''}".strip()


def _parse_attr(raw: str) -> dict:
    if "=" in raw:
        key, value = raw.split("=", 1)
        return {"name": key, "key": key, "value": value}
    return {"name": raw, "key": raw, "value": None}


if __name__ == "__main__":
    cli()
