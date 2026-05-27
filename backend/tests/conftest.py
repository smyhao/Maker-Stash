import os

import pytest

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
