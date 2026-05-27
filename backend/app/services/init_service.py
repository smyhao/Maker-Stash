from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app import models  # noqa: F401
from app.services.category_service import init_default_categories
from app.services.location_service import init_default_location


def create_schema() -> None:
    """Test-only schema bootstrap; runtime schema changes must use Alembic."""
    Base.metadata.create_all(bind=engine)


def run_migrations() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


def init_default_data(db: Session) -> None:
    init_default_categories(db)
    init_default_location(db)
