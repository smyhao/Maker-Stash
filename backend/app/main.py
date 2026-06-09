from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.response import app_error_handler, validation_error_handler


ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"


def mount_frontend(app: FastAPI) -> None:
    index_file = FRONTEND_DIST_DIR / "index.html"
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if not index_file.exists():
        return
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend_fallback(path: str) -> FileResponse:
        target = FRONTEND_DIST_DIR / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(index_file)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="workshop-stash")
    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(api_router)
    mount_frontend(app)
    return app


app = create_app()
