from datetime import datetime
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import NotFoundError
from app.models.backup import Backup


class BackupService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def create(self, include_uploads: bool = True, note: str | None = None, prefix: str = "backup") -> Backup:
        backup_dir = self.settings.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_id = f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        zip_path = backup_dir / f"{backup_id}.zip"
        db_path = self._sqlite_path()

        with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
            if db_path and db_path.exists():
                archive.write(db_path, "db.sqlite3")
            env_path = Path(".env")
            if env_path.exists():
                archive.write(env_path, ".env")
            if include_uploads and self.settings.upload_dir.exists():
                for path in self.settings.upload_dir.rglob("*"):
                    if path.is_file():
                        archive.write(path, Path("uploads") / path.relative_to(self.settings.upload_dir))

        backup = Backup(
            backup_id=backup_id,
            file_path=str(zip_path),
            size_bytes=zip_path.stat().st_size,
            include_uploads=include_uploads,
            note=note,
            status="success",
        )
        self.db.add(backup)
        self.db.commit()
        self.db.refresh(backup)
        return backup

    def list(self) -> list[Backup]:
        return list(self.db.scalars(select(Backup).order_by(Backup.created_at.desc())))

    def get_download_path(self, backup_id: str) -> tuple[Backup, Path]:
        backup = self.db.scalar(select(Backup).where(Backup.backup_id == backup_id))
        if backup is None:
            raise NotFoundError("BACKUP_NOT_FOUND", f"备份不存在：{backup_id}")
        path = Path(backup.file_path)
        if not path.exists():
            raise NotFoundError("BACKUP_NOT_FOUND", f"备份文件不存在：{backup.file_path}")
        return backup, path

    def restore(self, backup_id: str) -> Backup:
        backup = self.db.scalar(select(Backup).where(Backup.backup_id == backup_id))
        if backup is None:
            raise NotFoundError("BACKUP_NOT_FOUND", f"备份不存在：{backup_id}")
        backup_path = Path(backup.file_path)
        if not backup_path.exists():
            raise NotFoundError("BACKUP_NOT_FOUND", f"备份文件不存在：{backup.file_path}")

        self.create(include_uploads=True, note=f"恢复 {backup_id} 前自动快照", prefix="snapshot")
        self.db.commit()
        self.db.close()
        engine.dispose()

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with ZipFile(backup_path, "r") as archive:
                archive.extractall(tmp_path)
            self._restore_database(tmp_path)
            self._restore_uploads(tmp_path)

        return backup

    def _sqlite_path(self) -> Path | None:
        database_url = self.settings.database_url
        if not database_url.startswith("sqlite:///"):
            return None
        return Path(database_url.replace("sqlite:///", "", 1))

    def _restore_database(self, extracted_dir: Path) -> None:
        db_path = self._sqlite_path()
        source_db = extracted_dir / "db.sqlite3"
        if db_path is None or not source_db.exists():
            return
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_db, db_path)

    def _restore_uploads(self, extracted_dir: Path) -> None:
        source_uploads = extracted_dir / "uploads"
        if not source_uploads.exists():
            return
        if self.settings.upload_dir.exists():
            shutil.rmtree(self.settings.upload_dir)
        shutil.copytree(source_uploads, self.settings.upload_dir)
