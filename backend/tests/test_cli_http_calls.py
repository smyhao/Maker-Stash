import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from app.cli.main import cli


class FakeResponse:
    def __init__(self, payload: dict[str, Any] | None = None, content: bytes = b"") -> None:
        self._payload = payload or {"success": True, "data": {}}
        self.content = content
        self.status_code = 200

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def use_test_config(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "app.cli.client.load_config",
        lambda: {"api_url": "http://api.test", "token": "cli-token"},
    )


def test_item_add_posts_expected_payload(monkeypatch: Any) -> None:
    use_test_config(monkeypatch)
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse({"success": True, "data": {"code": "FIL-000001", "name": "黑色 PLA"}})

    monkeypatch.setattr("app.cli.client.httpx.request", fake_request)

    result = CliRunner().invoke(
        cli,
        [
            "item",
            "add",
            "--name",
            "黑色 PLA",
            "--category",
            "filament",
            "--quantity",
            "0.3",
            "--unit",
            "kg",
            "--tag",
            "PLA",
            "--attr",
            "color=black",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["code"] == "FIL-000001"
    assert calls == [
        {
            "method": "POST",
            "url": "http://api.test/api/items",
            "params": None,
            "json": {
                "name": "黑色 PLA",
                "category": "filament",
                "quantity": "0.3",
                "unit": "kg",
                "status": "normal",
                "tags": ["PLA"],
                "attributes": [{"name": "color", "key": "color", "value": "black"}],
            },
            "headers": {"Authorization": "Bearer cli-token"},
            "timeout": 15,
        }
    ]


def test_search_passes_query_filters_and_prints_json(monkeypatch: Any) -> None:
    use_test_config(monkeypatch)
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse({"success": True, "data": {"items": [{"code": "A1"}], "total": 1}})

    monkeypatch.setattr("app.cli.client.httpx.request", fake_request)

    result = CliRunner().invoke(
        cli,
        ["search", "pla", "--category", "filament", "--tag", "PLA", "--limit", "5", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["total"] == 1
    assert calls[0]["method"] == "GET"
    assert calls[0]["url"] == "http://api.test/api/search"
    assert calls[0]["params"] == {"q": "pla", "limit": 5, "category": "filament", "tag": "PLA"}
    assert calls[0]["headers"] == {"Authorization": "Bearer cli-token"}


def test_cli_api_error_is_reported(monkeypatch: Any) -> None:
    use_test_config(monkeypatch)

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse(
            {
                "success": False,
                "error": {"code": "ITEM_NOT_FOUND", "message": "物品不存在"},
            }
        )

    monkeypatch.setattr("app.cli.client.httpx.request", fake_request)

    result = CliRunner().invoke(cli, ["item", "show", "FIL-404"])

    assert result.exit_code != 0
    assert "ITEM_NOT_FOUND: 物品不存在" in result.output


def test_image_upload_uses_httpx_post_with_file_and_cover(monkeypatch: Any, tmp_path: Path) -> None:
    use_test_config(monkeypatch)
    image = tmp_path / "cover.png"
    image.write_bytes(b"png-data")
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        file_name, file_obj = kwargs["files"]["file"]
        calls.append(
            {
                "url": url,
                "file_name": file_name,
                "file_content": file_obj.read(),
                "data": kwargs["data"],
                "headers": kwargs["headers"],
                "timeout": kwargs["timeout"],
            }
        )
        return FakeResponse({"success": True, "data": {"original_name": "cover.png"}})

    monkeypatch.setattr("app.cli.client.httpx.post", fake_post)

    result = CliRunner().invoke(cli, ["image-add", "FIL-000001", str(image), "--cover"])

    assert result.exit_code == 0
    assert calls == [
        {
            "url": "http://api.test/api/items/FIL-000001/images",
            "file_name": "cover.png",
            "file_content": b"png-data",
            "data": {"is_cover": "true"},
            "headers": {"Authorization": "Bearer cli-token"},
            "timeout": 60,
        }
    ]


def test_backup_download_writes_response_bytes(monkeypatch: Any, tmp_path: Path) -> None:
    use_test_config(monkeypatch)
    output = tmp_path / "backup.zip"
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return FakeResponse(content=b"zip-bytes")

    monkeypatch.setattr("app.cli.client.httpx.get", fake_get)

    result = CliRunner().invoke(cli, ["backup", "download", "backup-001", "--output", str(output)])

    assert result.exit_code == 0
    assert output.read_bytes() == b"zip-bytes"
    assert calls == [
        {
            "url": "http://api.test/api/backups/backup-001/download",
            "headers": {"Authorization": "Bearer cli-token"},
            "timeout": 60,
        }
    ]
