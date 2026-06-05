from typing import Any

from fastapi import APIRouter, Query

from app.core.response import ok
from app.services.extension_service import ExtensionActionRequest, ExtensionService, ExtensionSettingsUpdate, ExtensionToggle


router = APIRouter(prefix="/extensions", tags=["extensions"])


@router.get("")
def list_extensions() -> dict[str, Any]:
    return ok(ExtensionService().list_extensions())


@router.patch("/{extension_id}")
def set_extension_enabled(extension_id: str, payload: ExtensionToggle) -> dict[str, Any]:
    return ok(ExtensionService().set_enabled(extension_id, payload.enabled))


@router.get("/{extension_id}/settings")
def get_extension_settings(extension_id: str) -> dict[str, Any]:
    return ok(ExtensionService().get_settings_payload(extension_id))


@router.patch("/{extension_id}/settings")
def update_extension_settings(extension_id: str, payload: ExtensionSettingsUpdate) -> dict[str, Any]:
    return ok(ExtensionService().update_settings(extension_id, payload.values))


@router.get("/contributions")
def list_extension_contributions(place: str | None = Query(default=None)) -> dict[str, Any]:
    return ok(ExtensionService().list_contributions(place))


@router.post("/{extension_id}/actions/{action}")
def run_extension_action(extension_id: str, action: str, payload: ExtensionActionRequest) -> dict[str, Any]:
    return ok(ExtensionService().run_action(extension_id, action, payload))
