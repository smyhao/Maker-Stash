from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.router import api_router
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.core.response import app_error_handler, validation_error_handler
from app.services.init_service import create_schema, init_default_data


def create_app() -> FastAPI:
    create_schema()
    with SessionLocal() as db:
        init_default_data(db)
    app = FastAPI(title="workshop-stash")
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(api_router)
    return app


app = create_app()
