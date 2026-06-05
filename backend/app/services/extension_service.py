import json
import re
from pathlib import Path
from typing import Any

from fastapi import status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError


EXTENSION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
SUPPORTED_SETTING_TYPES = {"string", "number", "boolean", "select", "multiselect", "secret", "path"}


class ExtensionToggle(BaseModel):
    enabled: bool


class ExtensionSettingsUpdate(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class ExtensionActionRequest(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
    source: str = "web"
    module: str | None = None
    operator: str | None = None


class ExtensionService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def list_extensions(self) -> dict[str, Any]:
        config = self._read_local_config()
        enabled = set(config.get("enabled", []))
        values = config.get("settings", {})
        extensions = []
        for manifest in self._discover_manifests():
            extension_id = manifest["id"]
            extension_values = values.get(extension_id, {})
            extensions.append(
                {
                    **manifest,
                    "enabled": extension_id in enabled,
                    "configured": self._is_configured(manifest, extension_values),
                    "settings_values": self._safe_settings_values(manifest, extension_values),
                }
            )
        return {"extensions": extensions}

    def set_enabled(self, extension_id: str, enabled: bool) -> dict[str, Any]:
        manifest = self._get_manifest(extension_id)
        config = self._read_local_config()
        enabled_ids = set(config.get("enabled", []))
        if enabled:
            enabled_ids.add(extension_id)
        else:
            enabled_ids.discard(extension_id)
        config["enabled"] = sorted(enabled_ids)
        self._write_local_config(config)
        values = config.get("settings", {}).get(extension_id, {})
        return {
            **manifest,
            "enabled": enabled,
            "configured": self._is_configured(manifest, values),
            "settings_values": self._safe_settings_values(manifest, values),
        }

    def get_settings_payload(self, extension_id: str) -> dict[str, Any]:
        manifest = self._get_manifest(extension_id)
        values = self._read_local_config().get("settings", {}).get(extension_id, {})
        return {
            "extension_id": extension_id,
            "schema": manifest.get("settings", {}).get("schema", {}),
            "values": self._safe_settings_values(manifest, values),
            "configured": self._is_configured(manifest, values),
        }

    def update_settings(self, extension_id: str, values: dict[str, Any]) -> dict[str, Any]:
        manifest = self._get_manifest(extension_id)
        schema = manifest.get("settings", {}).get("schema", {})
        cleaned = self._clean_settings_values(schema, values)
        config = self._read_local_config()
        all_settings = config.setdefault("settings", {})
        current = all_settings.get(extension_id, {})
        current.update(cleaned)
        all_settings[extension_id] = current
        self._write_local_config(config)
        return {
            "extension_id": extension_id,
            "schema": schema,
            "values": self._safe_settings_values(manifest, current),
            "configured": self._is_configured(manifest, current),
        }

    def list_contributions(self, place: str | None = None) -> dict[str, Any]:
        config = self._read_local_config()
        enabled = set(config.get("enabled", []))
        contributions = []
        for manifest in self._discover_manifests():
            extension_id = manifest["id"]
            if extension_id not in enabled:
                continue
            for contribution in manifest.get("contributions", []):
                if place and contribution.get("place") != place:
                    continue
                contributions.append(
                    {
                        **contribution,
                        "extension_id": extension_id,
                        "extension_name": manifest.get("name", extension_id),
                    }
                )
        return {"contributions": contributions}

    def run_action(self, extension_id: str, action: str, _: ExtensionActionRequest) -> dict[str, Any]:
        manifest = self._get_manifest(extension_id)
        config = self._read_local_config()
        if extension_id not in set(config.get("enabled", [])):
            raise AppError("EXTENSION_DISABLED", "扩展未启用", status.HTTP_409_CONFLICT)
        if not any(item.get("action") == action for item in manifest.get("contributions", [])):
            raise NotFoundError("EXTENSION_ACTION_NOT_FOUND", "扩展操作不存在")
        raise AppError("EXTENSION_ACTION_NOT_IMPLEMENTED", "扩展操作执行器尚未实现", status.HTTP_501_NOT_IMPLEMENTED)

    def _discover_manifests(self) -> list[dict[str, Any]]:
        extensions_dir = self.settings.extensions_dir
        if not extensions_dir.exists():
            return []
        manifests = []
        for manifest_path in sorted(extensions_dir.glob("*/extension.json")):
            manifest = self._read_manifest_file(manifest_path)
            if manifest:
                manifests.append(manifest)
        return manifests

    def _get_manifest(self, extension_id: str) -> dict[str, Any]:
        for manifest in self._discover_manifests():
            if manifest["id"] == extension_id:
                return manifest
        raise NotFoundError("EXTENSION_NOT_FOUND", "扩展不存在")

    def _read_manifest_file(self, path: Path) -> dict[str, Any] | None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        extension_id = raw.get("id")
        if not isinstance(extension_id, str) or not EXTENSION_ID_RE.match(extension_id):
            return None

        settings_schema = raw.get("settings", {}).get("schema", {})
        if not isinstance(settings_schema, dict):
            settings_schema = {}

        contributions = raw.get("contributions", [])
        if not isinstance(contributions, list):
            contributions = []

        return {
            "id": extension_id,
            "name": raw.get("name") or extension_id,
            "description": raw.get("description"),
            "version": raw.get("version") or "0.0.0",
            "api_version": raw.get("api_version") or "0.1",
            "settings": {"schema": self._clean_schema(settings_schema)},
            "contributions": self._clean_contributions(contributions),
        }

    def _clean_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}
        for key, field in schema.items():
            if not isinstance(key, str) or not isinstance(field, dict):
                continue
            field_type = field.get("type")
            if field_type not in SUPPORTED_SETTING_TYPES:
                continue
            cleaned[key] = {
                "type": field_type,
                "label": field.get("label") or key,
                "required": bool(field.get("required", False)),
                "default": field.get("default"),
                "options": field.get("options", []),
                "min": field.get("min"),
                "max": field.get("max"),
            }
        return cleaned

    def _clean_contributions(self, contributions: list[Any]) -> list[dict[str, Any]]:
        cleaned = []
        for contribution in contributions:
            if not isinstance(contribution, dict):
                continue
            place = contribution.get("place")
            action = contribution.get("action")
            label = contribution.get("label")
            contribution_type = contribution.get("type") or "button"
            if not all(isinstance(value, str) and value for value in (place, action, label)):
                continue
            cleaned.append(
                {
                    "place": place,
                    "type": contribution_type,
                    "label": label,
                    "action": action,
                    "requires": contribution.get("requires", []),
                }
            )
        return cleaned

    def _read_local_config(self) -> dict[str, Any]:
        path = self.settings.extensions_config_path
        if not path.exists():
            return {"enabled": [], "settings": {}}
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"enabled": [], "settings": {}}
        if not isinstance(config, dict):
            return {"enabled": [], "settings": {}}
        enabled = config.get("enabled", [])
        settings = config.get("settings", {})
        return {
            "enabled": enabled if isinstance(enabled, list) else [],
            "settings": settings if isinstance(settings, dict) else {},
        }

    def _write_local_config(self, config: dict[str, Any]) -> None:
        path = self.settings.extensions_config_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _clean_settings_values(self, schema: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}
        for key, field in schema.items():
            if key not in values:
                continue
            value = values[key]
            field_type = field.get("type")
            if field_type in {"string", "secret", "path", "select"}:
                cleaned[key] = "" if value is None else str(value)
            elif field_type == "number":
                cleaned[key] = value
            elif field_type == "boolean":
                cleaned[key] = bool(value)
            elif field_type == "multiselect":
                cleaned[key] = value if isinstance(value, list) else []
        return cleaned

    def _safe_settings_values(self, manifest: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        safe = {}
        schema = manifest.get("settings", {}).get("schema", {})
        for key, field in schema.items():
            value = values.get(key, field.get("default"))
            safe[key] = "********" if field.get("type") == "secret" and value else value
        return safe

    def _is_configured(self, manifest: dict[str, Any], values: dict[str, Any]) -> bool:
        schema = manifest.get("settings", {}).get("schema", {})
        for key, field in schema.items():
            if not field.get("required"):
                continue
            value = values.get(key, field.get("default"))
            if value is None or value == "" or value == []:
                return False
        return True
