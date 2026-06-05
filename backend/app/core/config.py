from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "workshop-stash"
    app_env: str = "development"
    database_url: str = "sqlite:///./data/db.sqlite3"
    upload_dir: Path = Path("./data/uploads")
    backup_dir: Path = Path("./data/backups")
    extensions_dir: Path = PROJECT_ROOT / "extensions"
    extensions_config_path: Path = Path("./data/extensions.local.json")
    max_upload_bytes: int = 50 * 1024 * 1024
    auth_login_enabled: bool = False
    api_token_enabled: bool = True
    api_token_require_all: bool = True
    web_ui_token_required: bool = False
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
