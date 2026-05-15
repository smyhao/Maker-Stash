from pathlib import Path

from app.cli.config import load_config, mask_token, save_config


def test_cli_config_roundtrip(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"

    save_config(
        {"api_url": "http://127.0.0.1:8000", "token": "secret-token"},
        config_file,
    )

    assert load_config(config_file) == {
        "api_url": "http://127.0.0.1:8000",
        "token": "secret-token",
    }


def test_mask_token() -> None:
    assert mask_token("") == ""
    assert mask_token("short") == "****"
    assert mask_token("abcd1234efgh") == "abcd...efgh"
