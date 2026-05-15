from pathlib import Path
import tomllib


DEFAULT_API_URL = "http://127.0.0.1:8000"


def config_path() -> Path:
    override = Path.home() / ".workshop-stash" / "config.toml"
    return override


def load_config(path: Path | None = None) -> dict[str, str]:
    target = path or config_path()
    if not target.exists():
        return {"api_url": DEFAULT_API_URL}
    with target.open("rb") as file:
        data = tomllib.load(file)
    return {
        "api_url": str(data.get("api_url") or DEFAULT_API_URL),
        "token": str(data.get("token") or ""),
    }


def save_config(config: dict[str, str], path: Path | None = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key in ("api_url", "token"):
        value = config.get(key)
        if value is not None:
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mask_token(token: str | None) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}...{token[-4:]}"
