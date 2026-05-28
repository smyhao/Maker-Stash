import os
import tempfile
from pathlib import Path

import pytest

# Keep pytest temp files out of the user temp directory and avoid reusing a
# fixed basetemp that Windows may keep locked between runs.
_pytest_temp_root = Path(__file__).resolve().parents[1] / ".pytest-runtime" / str(os.getpid())
_pytest_temp_root.mkdir(parents=True, exist_ok=True)
for _key in ("TMP", "TEMP", "TMPDIR"):
    os.environ[_key] = str(_pytest_temp_root)
tempfile.tempdir = str(_pytest_temp_root)

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("API_TOKEN_ENABLED", "false")

from app import models  # noqa: E402,F401
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.services.init_service import init_default_data  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        init_default_data(db)
    yield
    Base.metadata.drop_all(bind=engine)
