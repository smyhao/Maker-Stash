from fastapi import APIRouter, Depends

from app.api.routes import attachments, attributes, backups, categories, extensions, health, items, locations, metadata, search, stats, tasks, tokens, workflows
from app.core.security import require_api_token


api_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_token)])
api_router.include_router(health.router)
api_router.include_router(categories.router)
api_router.include_router(locations.router)
api_router.include_router(attributes.router)
api_router.include_router(metadata.router)
api_router.include_router(items.router)
api_router.include_router(search.router)
api_router.include_router(stats.router)
api_router.include_router(tasks.router)
api_router.include_router(workflows.router)
api_router.include_router(extensions.router)
api_router.include_router(attachments.router)
api_router.include_router(backups.router)
api_router.include_router(tokens.router)
