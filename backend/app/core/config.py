from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "workshop-stash"
    app_env: str = "development"
    database_url: str = "sqlite:///./data/db.sqlite3"
    upload_dir: Path = Path("./data/uploads")
    backup_dir: Path = Path("./data/backups")
    auth_login_enabled: bool = False
    api_token_enabled: bool = True
    api_token_require_all: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
