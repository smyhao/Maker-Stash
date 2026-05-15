from app.core.database import SessionLocal
from app.services.init_service import create_schema, init_default_data


def main() -> None:
    create_schema()
    with SessionLocal() as db:
        init_default_data(db)
    print("Database initialized.")


if __name__ == "__main__":
    main()
