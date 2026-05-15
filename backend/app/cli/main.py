from decimal import Decimal
from pathlib import Path

import click
import httpx

from app.cli.client import CliClient, echo_json
from app.cli.config import load_config, mask_token, save_config


@click.group()
def cli() -> None:
    """工坊物栈命令行客户端。"""


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


@cli.command()
def ping() -> None:
    data = CliClient().request("GET", "/api/health")
    click.echo(data.get("status", "ok"))


@cli.command()
@click.argument("query")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def search(query: str, as_json: bool) -> None:
    data = CliClient().request("GET", "/api/search", params={"q": query})
    if as_json:
        echo_json(data)
        return
    for item in data.get("items", []):
        quantity = _format_quantity(item.get("quantity"), item.get("unit"))
        click.echo(f"{item['code']:<12} {item['name']:<24} {quantity:<12} {item['status']}")


@cli.group()
def item() -> None:
    """管理物品。"""


@item.command("list")
@click.option("--category")
@click.option("--location")
@click.option("--restock", is_flag=True)
@click.option("--favorite", is_flag=True)
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_list(
    category: str | None,
    location: str | None,
    restock: bool,
    favorite: bool,
    as_json: bool,
) -> None:
    params = {
        "category": category,
        "location": location,
        "need_restock": True if restock else None,
        "favorite": True if favorite else None,
    }
    data = CliClient().request("GET", "/api/items", params={k: v for k, v in params.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    for row in data.get("items", []):
        quantity = _format_quantity(row.get("quantity"), row.get("unit"))
        click.echo(f"{row['code']:<12} {row['name']:<24} {quantity:<12} {row['status']}")


@item.command("show")
@click.argument("id_or_code")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_show(id_or_code: str, as_json: bool) -> None:
    data = CliClient().request("GET", f"/api/items/{id_or_code}")
    if as_json:
        echo_json(data)
        return
    click.echo(f"{data['code']}  {data['name']}")
    click.echo(f"状态: {data['status']}")
    click.echo(f"数量: {_format_quantity(data.get('quantity'), data.get('unit'))}")
    click.echo(f"位置文本: {data.get('location_text') or ''}")
    if data.get("description"):
        click.echo(f"备注: {data['description']}")


@item.command("add")
@click.option("--name", required=True)
@click.option("--category")
@click.option("--location", "location_code")
@click.option("--location-text")
@click.option("--quantity", type=Decimal)
@click.option("--unit")
@click.option("--note")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_add(
    name: str,
    category: str | None,
    location_code: str | None,
    location_text: str | None,
    quantity: Decimal | None,
    unit: str | None,
    note: str | None,
    as_json: bool,
) -> None:
    body = {
        "name": name,
        "category": category,
        "location_code": location_code,
        "location_text": location_text,
        "quantity": str(quantity) if quantity is not None else None,
        "unit": unit,
        "note": note,
    }
    data = CliClient().request("POST", "/api/items", json_body={k: v for k, v in body.items() if v is not None})
    if as_json:
        echo_json(data)
        return
    click.echo(f"已新增 {data['code']}  {data['name']}")


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
        json_body={
            "location_code": location_code,
            "location_text": location_text,
            "note": note,
            "source": "cli",
        },
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
def item_add_qty(
    id_or_code: str,
    amount: Decimal,
    unit: str | None,
    note: str | None,
    as_json: bool,
) -> None:
    data = _quantity_action(id_or_code, "add", amount, unit, note)
    if as_json:
        echo_json(data)
        return
    click.echo(f"当前数量: {_format_quantity(data.get('quantity'), data.get('unit'))}")


@item.command("use")
@click.argument("id_or_code")
@click.option("--amount", required=True, type=Decimal)
@click.option("--unit")
@click.option("--note")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_use(
    id_or_code: str,
    amount: Decimal,
    unit: str | None,
    note: str | None,
    as_json: bool,
) -> None:
    data = _quantity_action(id_or_code, "use", amount, unit, note)
    if as_json:
        echo_json(data)
        return
    click.echo(f"当前数量: {_format_quantity(data.get('quantity'), data.get('unit'))}")


@item.command("adjust")
@click.argument("id_or_code")
@click.option("--quantity", required=True, type=Decimal)
@click.option("--unit")
@click.option("--note")
@click.option("--json-output", "--json", "as_json", is_flag=True)
def item_adjust(
    id_or_code: str,
    quantity: Decimal,
    unit: str | None,
    note: str | None,
    as_json: bool,
) -> None:
    data = CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/adjust",
        json_body={
            "quantity": str(quantity),
            "unit": unit,
            "note": note,
            "source": "cli",
        },
    )
    if as_json:
        echo_json(data)
        return
    click.echo(f"当前数量: {_format_quantity(data.get('quantity'), data.get('unit'))}")


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
    data = CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/tags",
        json_body={"tags": list(tags)},
    )
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
    data = CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/aliases",
        json_body={"alias": alias_value},
    )
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
def item_bind(
    id_or_code: str,
    identifier_type: str,
    value: str,
    description: str | None,
) -> None:
    data = CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/identifiers",
        json_body={
            "type": identifier_type,
            "value": value,
            "description": description,
        },
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
        click.echo(row["name"])


@tag.command("add")
@click.argument("name")
@click.option("--slug")
def tag_add(name: str, slug: str | None) -> None:
    data = CliClient().request("POST", "/api/tags", json_body={"name": name, "slug": slug})
    click.echo(f"已新增标签 {data['name']}")


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
        click.echo(f"{row['id']:<4} {row['key']:<20} {row['name']:<20} {row['field_type']}")


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
        json_body={
            "name": name,
            "code": code,
            "parent_code": parent,
            "type": location_type,
            "description": description,
        },
    )
    if as_json:
        echo_json(data)
        return
    click.echo(f"已新增位置 {data['full_code']}  {data['name']}")


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
    config_data = load_config()
    api_url = config_data["api_url"].rstrip("/")
    token = config_data.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    target = output or Path(f"{backup_id}.zip")
    try:
        response = httpx.get(
            f"{api_url}/api/backups/{backup_id}/download",
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise click.ClickException(f"备份下载失败：{exc}") from exc
    target.write_bytes(response.content)
    click.echo(f"已下载到 {target}")


def _quantity_action(
    id_or_code: str,
    action: str,
    amount: Decimal,
    unit: str | None,
    note: str | None,
) -> dict:
    return CliClient().request(
        "POST",
        f"/api/items/{id_or_code}/{action}",
        json_body={
            "amount": str(amount),
            "unit": unit,
            "note": note,
            "source": "cli",
        },
    )


def _echo_location_node(row: dict, depth: int = 0) -> None:
    click.echo(f"{'  ' * depth}{row['code']}  {row['name']}")
    for child in row.get("children", []):
        _echo_location_node(child, depth + 1)


def _format_quantity(quantity: str | None, unit: str | None) -> str:
    if quantity is None:
        return ""
    return f"{quantity} {unit or ''}".strip()


if __name__ == "__main__":
    cli()
