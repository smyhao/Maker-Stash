from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.services.category_service import init_default_categories
from app.services.location_service import init_default_location


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


def init_default_data(db: Session) -> None:
    init_default_categories(db)
    init_default_location(db)
