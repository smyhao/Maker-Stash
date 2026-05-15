import json
from pathlib import Path
from typing import Any

import click
import httpx

from app.cli.config import load_config


class CliClient:
    def __init__(self) -> None:
        config = load_config()
        self.api_url = config["api_url"].rstrip("/")
        self.token = config.get("token") or ""

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = httpx.request(
                method,
                f"{self.api_url}{path}",
                params=params,
                json=json_body,
                headers=headers,
                timeout=15,
            )
        except httpx.HTTPError as exc:
            raise click.ClickException(f"API 请求失败：{exc}") from exc

        return _parse(response)

    def upload(
        self,
        path: str,
        file_path: Path,
        *,
        extra_fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with file_path.open("rb") as f:
                files = {"file": (file_path.name, f)}
                data = extra_fields or {}
                response = httpx.post(
                    f"{self.api_url}{path}",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60,
                )
        except httpx.HTTPError as exc:
            raise click.ClickException(f"上传失败：{exc}") from exc

        return _parse(response)

    def download(self, path: str, output: Path) -> None:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = httpx.get(
                f"{self.api_url}{path}",
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise click.ClickException(f"下载失败：{exc}") from exc
        output.write_bytes(response.content)


def _parse(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"API 返回不是 JSON：HTTP {response.status_code}") from exc

    if not payload.get("success"):
        error = payload.get("error") or {}
        code = error.get("code", "API_ERROR")
        message = error.get("message", "请求失败")
        raise click.ClickException(f"{code}: {message}")
    return payload.get("data")


def echo_json(data: Any) -> None:
    click.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))
