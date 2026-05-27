from pathlib import Path

from app.core.config import get_settings


def delete_upload_relative_file(relative_path: str | None) -> None:
    if not relative_path:
        return
    settings = get_settings()
    upload_root_parent = settings.upload_dir.parent.resolve()
    target = (upload_root_parent / relative_path).resolve()
    if not _is_relative_to(target, upload_root_parent):
        return
    if target.is_file():
        target.unlink(missing_ok=True)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
