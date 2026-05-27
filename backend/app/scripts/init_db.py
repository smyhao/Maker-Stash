from app.core.database import SessionLocal
from app.services.init_service import init_default_data, run_migrations


def main() -> None:
    run_migrations()
    with SessionLocal() as db:
        init_default_data(db)
    print("Database initialized.")


if __name__ == "__main__":
    main()
