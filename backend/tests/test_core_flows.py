import os
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["API_TOKEN_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import func, select, text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.audit import AuditLog, IdempotencyRecord  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.identifier import Identifier  # noqa: E402
from app.models.item import Item  # noqa: E402
from app.models.task import TaskJob  # noqa: E402
from app.services.backup_service import backup_lock  # noqa: E402
from app.services.init_service import create_schema, init_default_data  # noqa: E402
from app.services.task_service import TaskService  # noqa: E402


def test_sqlite_foreign_keys_are_enabled() -> None:
    with SessionLocal() as db:
        assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_item_rejects_missing_references() -> None:
    client = TestClient(create_app())

    missing_category = client.post(
        "/api/items",
        json={"name": "不存在分类", "category": "missing-category"},
    )
    assert missing_category.status_code == 404
    assert missing_category.json()["error"]["code"] == "CATEGORY_NOT_FOUND"

    missing_location = client.post(
        "/api/items",
        json={"name": "不存在位置", "category": "tools", "location_code": "WS.MISSING"},
    )
    assert missing_location.status_code == 404
    assert missing_location.json()["error"]["code"] == "LOCATION_NOT_FOUND"


def test_negative_quantity_is_rejected() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/items",
        json={"name": "库存边界", "category": "tools", "quantity": "1"},
    )
    assert created.status_code == 200
    item = created.json()["data"]

    negative_create = client.post(
        "/api/items",
        json={"name": "负库存", "category": "tools", "quantity": "-1"},
    )
    assert negative_create.status_code == 422
    assert negative_create.json()["error"]["code"] == "VALIDATION_ERROR"

    overuse = client.post(f"/api/items/{item['code']}/use", json={"amount": "2"})
    assert overuse.status_code == 400
    assert overuse.json()["error"]["code"] == "NEGATIVE_QUANTITY_NOT_ALLOWED"


def test_archived_item_rejects_quantity_and_move_writes() -> None:
    client = TestClient(create_app())

    location_response = client.post(
        "/api/locations",
        json={"name": "归档测试柜", "code": "ARC-CAB", "parent_code": "WS"},
    )
    assert location_response.status_code == 200

    created = client.post(
        "/api/items",
        json={"name": "归档边界", "category": "tools", "quantity": "1"},
    )
    assert created.status_code == 200
    code = created.json()["data"]["code"]

    archived = client.delete(f"/api/items/{code}")
    assert archived.status_code == 200

    add_response = client.post(f"/api/items/{code}/add", json={"amount": "1"})
    assert add_response.status_code == 400
    assert add_response.json()["error"]["code"] == "ARCHIVED_ITEM_QUANTITY_FORBIDDEN"

    move_response = client.post(
        f"/api/items/{code}/move",
        json={"location_code": "WS.ARC-CAB"},
    )
    assert move_response.status_code == 400
    assert move_response.json()["error"]["code"] == "ARCHIVED_ITEM_MOVE_FORBIDDEN"


def test_archived_item_update_cannot_bypass_quantity_or_location_guards() -> None:
    client = TestClient(create_app())

    location_response = client.post(
        "/api/locations",
        json={"name": "归档 PATCH 柜", "code": "ARC-PATCH", "parent_code": "WS"},
    )
    assert location_response.status_code == 200
    location = location_response.json()["data"]

    created = client.post(
        "/api/items",
        json={"name": "归档 PATCH 边界", "category": "tools", "quantity": "1"},
    )
    assert created.status_code == 200
    code = created.json()["data"]["code"]
    assert client.delete(f"/api/items/{code}").status_code == 200

    quantity_response = client.patch(f"/api/items/{code}", json={"quantity": "2"})
    assert quantity_response.status_code == 400
    assert quantity_response.json()["error"]["code"] == "ARCHIVED_ITEM_QUANTITY_FORBIDDEN"

    location_response = client.patch(f"/api/items/{code}", json={"location_id": location["id"]})
    assert location_response.status_code == 400
    assert location_response.json()["error"]["code"] == "ARCHIVED_ITEM_MOVE_FORBIDDEN"


def test_idempotent_item_create_replays_without_duplicate_write() -> None:
    client = TestClient(create_app())

    headers = {"Idempotency-Key": "create-item-001"}
    payload = {
        "name": "幂等创建",
        "category": "tools",
        "source": "web",
        "module": "inventory",
        "operator": "alice",
    }

    first = client.post("/api/items", json=payload, headers=headers)
    second = client.post("/api/items", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["code"] == first.json()["data"]["code"]

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Item).where(Item.name == "幂等创建")) == 1
        audit = db.scalar(select(AuditLog).where(AuditLog.request_id == "create-item-001"))
        assert audit is not None
        assert audit.action == "item.create"
        assert audit.source == "web"
        assert audit.module == "inventory"
        assert audit.who == "alice"


def test_idempotent_quantity_use_records_source_and_before_after_once() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/items",
        json={"name": "幂等库存", "category": "tools", "quantity": "5"},
    )
    code = created.json()["data"]["code"]
    payload = {
        "amount": "2",
        "source": "agent",
        "module": "restock-check",
        "operator": "ai-worker",
        "request_id": "use-qty-001",
    }

    first = client.post(f"/api/items/{code}/use", json=payload)
    second = client.post(f"/api/items/{code}/use", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["quantity"] == "3"

    with SessionLocal() as db:
        item = db.scalar(select(Item).where(Item.code == code))
        assert str(item.quantity) == "3.000"
        audits = list(db.scalars(select(AuditLog).where(AuditLog.request_id == "use-qty-001")))
        assert len(audits) == 1
        audit = audits[0]
        assert audit.action == "item.quantity.use"
        assert audit.source == "agent"
        assert audit.module == "restock-check"
        assert audit.who == "ai-worker"
        before = json.loads(audit.before_json)
        after = json.loads(audit.after_json)
        assert before["quantity"] == "5.000"
        assert after["quantity"] == "3.000"


def test_idempotent_identifier_binding_does_not_duplicate() -> None:
    client = TestClient(create_app())
    created = client.post("/api/items", json={"name": "绑定幂等", "category": "tools"})
    code = created.json()["data"]["code"]
    payload = {
        "type": "qrcode",
        "value": "QR-IDEMPOTENT-001",
        "source": "cli",
        "module": "scanner",
        "operator": "bob",
        "request_id": "bind-001",
    }

    first = client.post(f"/api/items/{code}/identifiers", json=payload)
    second = client.post(f"/api/items/{code}/identifiers", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["id"] == first.json()["data"]["id"]

    with SessionLocal() as db:
        assert db.scalar(
            select(func.count()).select_from(Identifier).where(Identifier.value == "QR-IDEMPOTENT-001")
        ) == 1
        record = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.request_id == "bind-001"))
        assert record is not None
        assert record.action == "identifier.bind"
        audit = db.scalar(select(AuditLog).where(AuditLog.request_id == "bind-001"))
        assert audit is not None
        assert audit.action == "identifier.bind"


def test_idempotency_key_mismatch_returns_stable_error() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/items",
        json={"name": "幂等冲突", "category": "tools", "request_id": "body-key"},
        headers={"Idempotency-Key": "header-key"},
    )

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_MISMATCH"


def test_task_can_be_created_and_status_queried() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "job_type": "batch_import",
            "input_summary": "导入 10 条采购记录",
            "source": "web",
            "module": "purchase-import",
            "operator": "alice",
            "request_id": "task-create-001",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "queued"
    assert data["task_id"].startswith("task-")
    task = data["task"]
    assert task["task_id"] == data["task_id"]
    assert task["status"] == "queued"
    assert task["job_type"] == "batch_import"
    assert task["source"] == "web"
    assert task["module"] == "purchase-import"
    assert task["operator"] == "alice"
    assert task["request_id"] == "task-create-001"

    status_response = client.get(f"/api/tasks/{data['task_id']}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()["data"]["task"]
    assert status_data["task_id"] == data["task_id"]
    assert status_data["status"] == "queued"
    assert status_data["error"] is None


def test_task_submit_is_idempotent_by_header_key() -> None:
    client = TestClient(create_app())
    headers = {"Idempotency-Key": "task-idempotent-001"}
    payload = {"job_type": "batch_outbound", "input_summary": "按项目清单出库"}

    first = client.post("/api/tasks", json=payload, headers=headers)
    second = client.post("/api/tasks", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["task_id"] == first.json()["data"]["task_id"]


def test_failed_task_status_returns_clear_error_shape() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/tasks",
        json={"job_type": "batch_import", "input_summary": "导入格式错误样例"},
    )
    task_id = created.json()["data"]["task_id"]

    with SessionLocal() as db:
        TaskService(db).mark_failed(task_id, "CSV 缺少必填列 name")

    status_response = client.get(f"/api/tasks/{task_id}/status")

    assert status_response.status_code == 200
    task = status_response.json()["data"]["task"]
    assert task["task_id"] == task_id
    assert task["status"] == "failed"
    assert task["error"] == {
        "code": "TASK_FAILED",
        "message": "CSV 缺少必填列 name",
    }


def test_missing_task_returns_stable_error_code() -> None:
    client = TestClient(create_app())

    response = client.get("/api/tasks/task-missing/status")

    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_batch_import_plan_only_previews_without_business_write() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/workflows/plans",
        json={
            "workflow_type": "batch_import",
            "import_rows": [
                {
                    "name": "计划导入 PLA",
                    "category": "filament",
                    "quantity": "2",
                    "unit": "kg",
                }
            ],
            "source": "agent",
            "module": "importer",
            "operator": "planner",
            "request_id": "plan-import-001",
        },
    )

    assert response.status_code == 200
    plan = response.json()["data"]["plan"]
    assert plan["workflow_type"] == "batch_import"
    assert plan["status"] == "planned"
    assert plan["summary"] == {"creates": 1, "updates": 0, "skips": 0, "failures": 0, "risks": 0}
    assert plan["creates"][0]["after"]["name"] == "计划导入 PLA"
    assert plan["confirm_token"].startswith("confirm-")

    items = client.get("/api/items?q=计划导入 PLA")
    assert items.status_code == 200
    assert items.json()["data"]["total"] == 0


def test_batch_import_confirm_executes_once_and_records_task_and_audit() -> None:
    client = TestClient(create_app())
    plan_response = client.post(
        "/api/workflows/plans",
        json={
            "workflow_type": "batch_import",
            "import_rows": [{"name": "确认导入 PLA", "category": "filament", "quantity": "1", "unit": "kg"}],
            "source": "agent",
            "module": "importer",
            "operator": "planner",
            "request_id": "plan-import-002",
        },
    )
    plan = plan_response.json()["data"]["plan"]

    first = client.post(
        f"/api/workflows/plans/{plan['plan_id']}/confirm",
        json={
            "confirm_token": plan["confirm_token"],
            "source": "agent",
            "module": "importer",
            "operator": "executor",
            "request_id": "confirm-import-002",
        },
    )
    second = client.post(
        f"/api/workflows/plans/{plan['plan_id']}/confirm",
        json={
            "confirm_token": plan["confirm_token"],
            "source": "agent",
            "module": "importer",
            "operator": "executor",
            "request_id": "confirm-import-002",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    data = second.json()["data"]
    assert data["plan"]["status"] == "confirmed"
    assert data["task"]["status"] == "succeeded"
    assert data["result"]["summary"] == {"created": 1, "updated": 0, "skipped": 0, "failed": 0}

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Item).where(Item.name == "确认导入 PLA")) == 1
        audits = list(db.scalars(select(AuditLog).where(AuditLog.action == "item.create", AuditLog.request_id.like("confirm-import-002%"))))
        assert len(audits) == 1
        assert audits[0].source == "agent"
        assert audits[0].module == "importer"
        assert audits[0].who == "executor"


def test_batch_outbound_plan_and_confirm_updates_stock_once() -> None:
    client = TestClient(create_app())
    item_response = client.post(
        "/api/items",
        json={"name": "计划出库物品", "category": "tools", "quantity": "5"},
    )
    code = item_response.json()["data"]["code"]

    plan_response = client.post(
        "/api/workflows/plans",
        json={
            "workflow_type": "batch_outbound",
            "outbound_rows": [{"id_or_code": code, "amount": "2", "note": "项目领用"}],
            "source": "web",
            "module": "project-outbound",
            "operator": "alice",
            "request_id": "plan-outbound-001",
        },
    )
    plan = plan_response.json()["data"]["plan"]
    assert plan["summary"]["updates"] == 1
    assert plan["updates"][0]["before"]["quantity"] == "5.000"
    assert plan["updates"][0]["after"]["quantity"] == "3"

    before_confirm = client.get(f"/api/items/{code}")
    assert before_confirm.json()["data"]["quantity"] == "5"

    first = client.post(
        f"/api/workflows/plans/{plan['plan_id']}/confirm",
        json={"confirm_token": plan["confirm_token"], "request_id": "confirm-outbound-001"},
    )
    second = client.post(
        f"/api/workflows/plans/{plan['plan_id']}/confirm",
        json={"confirm_token": plan["confirm_token"], "request_id": "confirm-outbound-001"},
    )
    assert first.status_code == 200
    assert second.status_code == 200

    item_after = client.get(f"/api/items/{code}")
    assert item_after.json()["data"]["quantity"] == "3"


def test_batch_import_confirm_failure_rolls_back_partial_business_writes() -> None:
    client = TestClient(create_app())
    plan_response = client.post(
        "/api/workflows/plans",
        json={
            "workflow_type": "batch_import",
            "import_rows": [
                {"name": "原子导入先成功项", "category": "filament", "quantity": "1"},
                {"name": "原子导入后失败项", "category": "tools", "quantity": "1"},
            ],
            "request_id": "plan-import-atomic-001",
        },
    )
    plan = plan_response.json()["data"]["plan"]
    assert plan["summary"]["failures"] == 0

    with SessionLocal() as db:
        category = db.scalar(select(Category).where(Category.slug == "tools"))
        assert category is not None
        db.delete(category)
        db.commit()

    confirm = client.post(
        f"/api/workflows/plans/{plan['plan_id']}/confirm",
        json={"confirm_token": plan["confirm_token"], "request_id": "confirm-import-atomic-001"},
    )
    assert confirm.status_code == 404
    assert confirm.json()["error"]["code"] == "CATEGORY_NOT_FOUND"

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Item).where(Item.name == "原子导入先成功项")) == 0
        task = db.scalar(select(TaskJob).where(TaskJob.request_id == "confirm-import-atomic-001:task"))
        assert task is not None
        assert task.status == "failed"
        assert task.error_message == "分类不存在：tools"


def test_plan_with_failures_cannot_be_confirmed() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/workflows/plans",
        json={
            "workflow_type": "batch_outbound",
            "outbound_rows": [{"id_or_code": "MISSING-001", "amount": "1"}],
        },
    )
    plan = response.json()["data"]["plan"]
    assert plan["summary"]["failures"] == 1

    confirm = client.post(
        f"/api/workflows/plans/{plan['plan_id']}/confirm",
        json={"confirm_token": plan["confirm_token"]},
    )
    assert confirm.status_code == 409
    assert confirm.json()["error"]["code"] == "PLAN_HAS_FAILURES"


def test_agent_operation_plan_contract_is_stable() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/workflows/plans",
        json={
            "workflow_type": "agent_operation",
            "agent_actions": [
                {
                    "action": "suggest_move",
                    "target_type": "item",
                    "target_ref": "FIL-000001",
                    "summary": "建议移动到干燥柜",
                    "risk": "需要人工确认实际位置",
                }
            ],
        },
    )
    assert response.status_code == 200
    plan = response.json()["data"]["plan"]
    assert plan["workflow_type"] == "agent_operation"
    assert plan["summary"] == {"creates": 0, "updates": 1, "skips": 0, "failures": 0, "risks": 1}
    assert plan["risks"] == ["需要人工确认实际位置"]


def test_item_location_quantity_and_search_flow() -> None:
    client = TestClient(create_app())

    location_response = client.post(
        "/api/locations",
        json={"name": "A柜", "code": "CAB-A", "parent_code": "WS", "type": "cabinet"},
    )
    assert location_response.status_code == 200

    item_response = client.post(
        "/api/items",
        json={
            "name": "黑色 PLA",
            "category": "filament",
            "location_code": "WS.CAB-A",
            "quantity": "0.42",
            "unit": "kg",
            "note": "测试新增",
        },
    )
    assert item_response.status_code == 200
    item = item_response.json()["data"]
    assert item["code"] == "FIL-000001"

    use_response = client.post(
        f"/api/items/{item['code']}/use",
        json={"amount": "0.12", "unit": "kg", "note": "打印测试件"},
    )
    assert use_response.status_code == 200
    assert use_response.json()["data"]["quantity"] == "0.3"

    search_response = client.get("/api/search?q=PLA")
    assert search_response.status_code == 200
    assert search_response.json()["data"]["items"][0]["code"] == "FIL-000001"


def test_delete_item_can_soft_delete_attachments() -> None:
    client = TestClient(create_app())
    item_response = client.post("/api/items", json={"name": "测试工具", "category": "tools"})
    item = item_response.json()["data"]

    delete_response = client.delete(f"/api/items/{item['code']}?delete_attachments=true")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"] == {
        "archived": True,
        "attachments_deleted": True,
    }


def test_deleting_cover_attachment_clears_item_cover_reference(tmp_path: Path) -> None:
    settings = get_settings()
    old_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path / "uploads"
    try:
        client = TestClient(create_app())
        item_response = client.post("/api/items", json={"name": "封面删除测试", "category": "tools"})
        item = item_response.json()["data"]

        image_file = BytesIO()
        Image.new("RGB", (240, 180), color=(20, 80, 120)).save(image_file, format="PNG")
        image_file.seek(0)

        upload_response = client.post(
            f"/api/items/{item['code']}/images?is_cover=true",
            files={"file": ("cover.png", image_file.getvalue(), "image/png")},
        )
        assert upload_response.status_code == 200
        attachment = upload_response.json()["data"]
        attachment_id = attachment["id"]
        original_path = settings.upload_dir.parent / attachment["file_path"]
        thumbnail_path = settings.upload_dir.parent / attachment["thumbnail_path"]
        assert original_path.exists()
        assert thumbnail_path.exists()

        with_cover = client.get(f"/api/items/{item['code']}")
        assert with_cover.status_code == 200
        assert with_cover.json()["data"]["cover_attachment_id"] == attachment_id

        delete_response = client.delete(f"/api/attachments/{attachment_id}")
        assert delete_response.status_code == 200
        assert not original_path.exists()
        assert not thumbnail_path.exists()

        without_cover = client.get(f"/api/items/{item['code']}")
        assert without_cover.status_code == 200
        assert without_cover.json()["data"]["cover_attachment_id"] is None

        thumbnail_response = client.get(f"/api/attachments/{attachment_id}/thumbnail")
        assert thumbnail_response.status_code == 404
    finally:
        settings.upload_dir = old_upload_dir


def test_archive_with_attachment_delete_releases_files(tmp_path: Path) -> None:
    settings = get_settings()
    old_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path / "uploads"
    try:
        client = TestClient(create_app())
        item_response = client.post("/api/items", json={"name": "附件释放测试", "category": "tools"})
        item = item_response.json()["data"]

        attachment_response = client.post(
            f"/api/items/{item['code']}/attachments",
            files={"file": ("manual.txt", b"manual", "text/plain")},
        )
        assert attachment_response.status_code == 200
        attachment = attachment_response.json()["data"]
        attachment_path = settings.upload_dir.parent / attachment["file_path"]
        assert attachment_path.exists()

        image_file = BytesIO()
        Image.new("RGB", (240, 180), color=(20, 80, 120)).save(image_file, format="PNG")
        image_file.seek(0)
        image_response = client.post(
            f"/api/items/{item['code']}/images?is_cover=true",
            files={"file": ("cover.png", image_file.getvalue(), "image/png")},
        )
        assert image_response.status_code == 200
        image = image_response.json()["data"]
        image_path = settings.upload_dir.parent / image["file_path"]
        thumbnail_path = settings.upload_dir.parent / image["thumbnail_path"]
        assert image_path.exists()
        assert thumbnail_path.exists()

        delete_response = client.delete(f"/api/items/{item['code']}?delete_attachments=true")
        assert delete_response.status_code == 200
        assert not attachment_path.exists()
        assert not image_path.exists()
        assert not thumbnail_path.exists()

        archived = client.get(f"/api/items/{item['code']}")
        assert archived.status_code == 200
        assert archived.json()["data"]["cover_attachment_id"] is None
    finally:
        settings.upload_dir = old_upload_dir


def test_replacing_cover_clears_previous_cover_flag(tmp_path: Path) -> None:
    settings = get_settings()
    old_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path / "uploads"
    try:
        client = TestClient(create_app())
        item_response = client.post("/api/items", json={"name": "封面替换测试", "category": "tools"})
        item = item_response.json()["data"]

        first_image = BytesIO()
        Image.new("RGB", (240, 180), color=(20, 80, 120)).save(first_image, format="PNG")
        first_image.seek(0)
        first_upload = client.post(
            f"/api/items/{item['code']}/images?is_cover=true",
            files={"file": ("first.png", first_image.getvalue(), "image/png")},
        )
        assert first_upload.status_code == 200
        first_id = first_upload.json()["data"]["id"]

        second_image = BytesIO()
        Image.new("RGB", (240, 180), color=(120, 80, 20)).save(second_image, format="PNG")
        second_image.seek(0)
        second_upload = client.post(
            f"/api/items/{item['code']}/images?is_cover=true",
            files={"file": ("second.png", second_image.getvalue(), "image/png")},
        )
        assert second_upload.status_code == 200
        second_id = second_upload.json()["data"]["id"]

        refreshed = client.get(f"/api/items/{item['code']}")
        assert refreshed.status_code == 200
        assert refreshed.json()["data"]["cover_attachment_id"] == second_id

        attachments = client.get(f"/api/items/{item['code']}/attachments").json()["data"]["attachments"]
        first = next(attachment for attachment in attachments if attachment["id"] == first_id)
        second = next(attachment for attachment in attachments if attachment["id"] == second_id)
        assert first["is_cover"] is False
        assert second["is_cover"] is True
    finally:
        settings.upload_dir = old_upload_dir


def test_tags_aliases_and_identifier_flow() -> None:
    client = TestClient(create_app())
    item_response = client.post(
        "/api/items",
        json={
            "name": "ESP32-S3 模块",
            "category": "components",
            "tags": ["乐鑫", "开发板"],
        },
    )
    assert item_response.status_code == 200
    item = item_response.json()["data"]

    tag_search = client.get("/api/search?q=乐鑫")
    assert tag_search.status_code == 200
    assert tag_search.json()["data"]["items"][0]["code"] == item["code"]

    alias_response = client.post(
        f"/api/items/{item['code']}/aliases",
        json={"alias": "WiFi模块"},
    )
    assert alias_response.status_code == 200

    alias_search = client.get("/api/search?q=WiFi")
    assert alias_search.status_code == 200
    assert alias_search.json()["data"]["items"][0]["code"] == item["code"]

    identifier_response = client.post(
        f"/api/items/{item['code']}/identifiers",
        json={"type": "qrcode", "value": "QR-ELE-TEST"},
    )
    assert identifier_response.status_code == 200

    found_response = client.get("/api/items/by-identifier/QR-ELE-TEST")
    assert found_response.status_code == 200
    assert found_response.json()["data"]["code"] == item["code"]


def test_tree_endpoints_and_item_pagination() -> None:
    client = TestClient(create_app())

    parent_response = client.post(
        "/api/locations",
        json={"name": "B柜", "code": "CAB-B", "parent_code": "WS", "type": "cabinet"},
    )
    assert parent_response.status_code == 200
    child_response = client.post(
        "/api/locations",
        json={"name": "第一层", "code": "S01", "parent_code": "WS.CAB-B", "type": "shelf"},
    )
    assert child_response.status_code == 200

    tree_response = client.get("/api/locations/tree")
    assert tree_response.status_code == 200
    roots = tree_response.json()["data"]["locations"]
    ws = next(location for location in roots if location["full_code"] == "WS")
    cab_b = next(location for location in ws["children"] if location["full_code"] == "WS.CAB-B")
    assert cab_b["children"][0]["full_code"] == "WS.CAB-B.S01"

    category_tree_response = client.get("/api/categories/tree")
    assert category_tree_response.status_code == 200
    assert category_tree_response.json()["data"]["categories"][0]["children"] == []

    for index in range(3):
        response = client.post(
            "/api/items",
            json={"name": f"分页测试 {index}", "category": "tools"},
        )
        assert response.status_code == 200

    page_response = client.get("/api/items?q=分页测试&page=1&page_size=2")
    assert page_response.status_code == 200
    data = page_response.json()["data"]
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2


def test_attribute_definition_and_item_attribute_flow() -> None:
    client = TestClient(create_app())
    categories = client.get("/api/categories").json()["data"]["categories"]
    filament = next(category for category in categories if category["slug"] == "filament")

    definition_response = client.post(
        "/api/attribute-definitions",
        json={
            "category_id": filament["id"],
            "name": "颜色",
            "key": "color",
            "field_type": "text",
        },
    )
    assert definition_response.status_code == 200
    definition = definition_response.json()["data"]

    item_response = client.post(
        "/api/items",
        json={"name": "属性测试 PLA", "category": "filament"},
    )
    item = item_response.json()["data"]

    value_response = client.post(
        f"/api/items/{item['code']}/attributes",
        json={
            "attribute_definition_id": definition["id"],
            "name": "颜色",
            "key": "color",
            "value": "黑色",
        },
    )
    assert value_response.status_code == 200
    value = value_response.json()["data"]
    assert value["value"] == "黑色"

    listed_response = client.get(f"/api/items/{item['code']}/attributes")
    assert listed_response.status_code == 200
    assert listed_response.json()["data"]["attributes"][0]["key"] == "color"

    update_response = client.patch(
        f"/api/item-attributes/{value['id']}",
        json={"value": "白色"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["value"] == "白色"


def test_system_info_and_validation_error_shape() -> None:
    client = TestClient(create_app())

    info_response = client.get("/api/system/info")
    assert info_response.status_code == 200
    info = info_response.json()["data"]
    assert info["counts"]["categories"] >= 1
    assert "auth" in info

    invalid_response = client.post("/api/locations", json={"name": "缺少 code"})
    assert invalid_response.status_code == 422
    body = invalid_response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_tag_delete_and_item_tag_status_filters() -> None:
    client = TestClient(create_app())

    tag_response = client.post("/api/tags", json={"name": "测试标签"})
    assert tag_response.status_code == 200
    tag_id = tag_response.json()["data"]["id"]

    item_response = client.post(
        "/api/items",
        json={"name": "过滤测试", "category": "tools", "tags": ["测试标签"]},
    )
    assert item_response.status_code == 200
    item = item_response.json()["data"]

    tagged = client.get("/api/items?tag=测试标签")
    assert tagged.status_code == 200
    assert any(i["code"] == item["code"] for i in tagged.json()["data"]["items"])

    status_filtered = client.get("/api/items?status=normal")
    assert status_filtered.status_code == 200
    assert any(i["code"] == item["code"] for i in status_filtered.json()["data"]["items"])

    delete_tag_response = client.delete(f"/api/tags/{tag_id}")
    assert delete_tag_response.status_code == 200
    assert delete_tag_response.json()["data"]["deleted"] is True


def test_location_items_by_id() -> None:
    client = TestClient(create_app())

    loc_response = client.post(
        "/api/locations",
        json={"name": "过滤位置", "code": "FLT-LOC", "parent_code": "WS"},
    )
    assert loc_response.status_code == 200
    loc = loc_response.json()["data"]

    client.post(
        "/api/items",
        json={"name": "位置过滤物品", "category": "tools", "location_code": loc["full_code"]},
    )

    items_response = client.get(f"/api/locations/{loc['id']}/items")
    assert items_response.status_code == 200
    items = items_response.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["location_id"] == loc["id"]


def test_search_with_filters_and_rich_results() -> None:
    client = TestClient(create_app())

    client.post(
        "/api/items",
        json={"name": "搜索测试电阻", "category": "components", "tags": ["10k"]},
    )

    search_response = client.get("/api/search?q=搜索测试电阻")
    assert search_response.status_code == 200
    results = search_response.json()["data"]["items"]
    assert len(results) >= 1
    result = results[0]
    assert "category_name" in result
    assert "location_full_code" in result
    assert "matched_by" in result
    assert "need_restock" in result
    assert "is_favorite" in result

    filtered = client.get("/api/search?q=电阻&category=components")
    assert filtered.status_code == 200
    assert len(filtered.json()["data"]["items"]) >= 1


def test_notes_with_operator_and_metadata() -> None:
    client = TestClient(create_app())

    item_response = client.post(
        "/api/items",
        json={"name": "备注测试", "category": "tools"},
    )
    item = item_response.json()["data"]

    note_response = client.post(
        f"/api/items/{item['code']}/notes",
        json={
            "note_type": "note",
            "content": "带操作者的备注",
            "source": "web",
            "operator": "admin",
            "metadata_json": '{"key": "value"}',
        },
    )
    assert note_response.status_code == 200

    notes_response = client.get(f"/api/items/{item['code']}/notes")
    assert notes_response.status_code == 200
    notes = notes_response.json()["data"]["notes"]
    assert any(n["operator"] == "admin" for n in notes)
    assert any(n["source"] == "web" for n in notes)
    assert "quantity_change" in notes[0]
    assert "quantity_after" in notes[0]
    assert "metadata_json" in notes[0]


def test_fulltext_search_covers_all_dimensions() -> None:
    client = TestClient(create_app())

    client.post("/api/locations", json={"name": "干燥柜", "code": "DRY-CAB", "parent_code": "WS"})

    item_resp = client.post(
        "/api/items",
        json={
            "name": "ESP32-C3",
            "category": "components",
            "location_code": "WS.DRY-CAB",
            "tags": ["乐鑫"],
            "description": "低功耗蓝牙芯片",
        },
    )
    code = item_resp.json()["data"]["code"]

    client.post(f"/api/items/{code}/aliases", json={"alias": "小蓝片"})
    client.post(f"/api/items/{code}/attributes", json={"name": "封装", "key": "package", "value": "QFN32"})
    client.post(f"/api/items/{code}/notes", json={"content": "已到货待测试", "source": "web"})

    # 按名称搜索
    assert client.get("/api/search?q=ESP32").json()["data"]["items"]

    # 按别名搜索
    results = client.get("/api/search?q=小蓝片").json()["data"]["items"]
    assert any(r["code"] == code for r in results)

    # 按标签搜索
    results = client.get("/api/search?q=乐鑫").json()["data"]["items"]
    assert any(r["code"] == code for r in results)

    # 按属性搜索
    results = client.get("/api/search?q=QFN32").json()["data"]["items"]
    assert any(r["code"] == code for r in results)

    # 按备注搜索
    results = client.get("/api/search?q=待测试").json()["data"]["items"]
    assert any(r["code"] == code for r in results)

    # 按位置名称搜索
    results = client.get("/api/search?q=干燥柜").json()["data"]["items"]
    assert any(r["code"] == code for r in results)

    # 按描述搜索
    results = client.get("/api/search?q=低功耗").json()["data"]["items"]
    assert any(r["code"] == code for r in results)

    # matched_by 标记准确
    result = client.get("/api/search?q=小蓝片").json()["data"]["items"][0]
    assert "alias" in result["matched_by"]


def test_item_list_q_also_uses_fulltext() -> None:
    client = TestClient(create_app())

    client.post(
        "/api/items",
        json={"name": "全量搜索验证", "category": "tools", "tags": ["专用标签_xyz"]},
    )

    # 物品列表 q 参数能搜到标签
    resp = client.get("/api/items?q=专用标签_xyz")
    assert resp.status_code == 200
    assert any(item["name"] == "全量搜索验证" for item in resp.json()["data"]["items"])


def test_upload_limits_and_image_mime_validation(tmp_path: Path) -> None:
    settings = get_settings()
    old_upload_dir = settings.upload_dir
    old_max_upload_bytes = settings.max_upload_bytes
    settings.upload_dir = tmp_path / "uploads"
    settings.max_upload_bytes = 4
    try:
        client = TestClient(create_app())
        item_response = client.post("/api/items", json={"name": "上传限制测试", "category": "tools"})
        item = item_response.json()["data"]

        too_large = client.post(
            f"/api/items/{item['code']}/attachments",
            files={"file": ("large.txt", b"12345", "text/plain")},
        )
        assert too_large.status_code == 413
        assert too_large.json()["error"]["code"] == "UPLOAD_TOO_LARGE"

        bad_image = client.post(
            f"/api/items/{item['code']}/images",
            files={"file": ("not-image.txt", b"123", "text/plain")},
        )
        assert bad_image.status_code == 400
        assert bad_image.json()["error"]["code"] == "UPLOAD_FAILED"
    finally:
        settings.upload_dir = old_upload_dir
        settings.max_upload_bytes = old_max_upload_bytes


def test_image_upload_creates_thumbnail(tmp_path: Path) -> None:
    settings = get_settings()
    old_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path / "uploads"
    try:
        client = TestClient(create_app())
        item_response = client.post("/api/items", json={"name": "缩略图测试", "category": "tools"})
        item = item_response.json()["data"]

        image_file = BytesIO()
        Image.new("RGB", (800, 600), color=(40, 120, 200)).save(image_file, format="PNG")
        image_file.seek(0)

        upload_response = client.post(
            f"/api/items/{item['code']}/images?is_cover=true",
            files={"file": ("part.png", image_file.getvalue(), "image/png")},
        )
        assert upload_response.status_code == 200
        attachment = upload_response.json()["data"]
        assert attachment["thumbnail_path"] == f"uploads/thumbnails/{Path(attachment['stored_name']).stem}.jpg"

        thumbnail_response = client.get(f"/api/attachments/{attachment['id']}/thumbnail")
        assert thumbnail_response.status_code == 200
        assert thumbnail_response.headers["content-type"] == "image/jpeg"

        with Image.open(BytesIO(thumbnail_response.content)) as thumbnail:
            assert thumbnail.width <= 320
            assert thumbnail.height <= 240
    finally:
        settings.upload_dir = old_upload_dir


def test_token_management_flow() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/tokens",
        json={"name": "web-test", "description": "前端测试 Token"},
    )
    assert created.status_code == 200
    token_data = created.json()["data"]
    plaintext = token_data["token"]
    assert plaintext
    assert token_data["name"] == "web-test"
    assert token_data["enabled"] is True

    duplicate = client.post("/api/tokens", json={"name": "web-test"})
    assert duplicate.status_code == 400
    assert duplicate.json()["error"]["code"] == "DUPLICATE_NAME"

    listed = client.get(f"/api/tokens?current_token={plaintext}")
    assert listed.status_code == 200
    tokens = listed.json()["data"]["tokens"]
    current = next(token for token in tokens if token["id"] == token_data["id"])
    assert current["is_current"] is True
    assert "token" not in current

    updated = client.patch(
        f"/api/tokens/{token_data['id']}",
        json={"enabled": False, "description": "已禁用"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["enabled"] is False
    assert updated.json()["data"]["description"] == "已禁用"

    deleted = client.delete(f"/api/tokens/{token_data['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True

    missing = client.patch(f"/api/tokens/{token_data['id']}", json={"enabled": True})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "TOKEN_NOT_FOUND"


def test_backup_create_download_restore_and_lock(tmp_path: Path) -> None:
    settings = get_settings()
    old_upload_dir = settings.upload_dir
    old_backup_dir = settings.backup_dir
    settings.upload_dir = tmp_path / "uploads"
    settings.backup_dir = tmp_path / "backups"
    try:
        upload_file = settings.upload_dir / "attachments" / "datasheet.txt"
        upload_file.parent.mkdir(parents=True, exist_ok=True)
        upload_file.write_text("datasheet-v1", encoding="utf-8")

        client = TestClient(create_app())

        locked = backup_lock.acquire(blocking=False)
        assert locked is True
        try:
            busy = client.post("/api/backups", json={"include_uploads": True})
            assert busy.status_code == 409
            assert busy.json()["error"]["code"] == "BACKUP_IN_PROGRESS"
        finally:
            backup_lock.release()

        created = client.post(
            "/api/backups",
            json={"include_uploads": True, "note": "测试备份"},
        )
        assert created.status_code == 200
        backup = created.json()["data"]
        assert backup["backup_id"].startswith("backup-")
        assert backup["include_uploads"] is True
        assert backup["note"] == "测试备份"

        backup_path = Path(backup["file_path"])
        assert backup_path.exists()
        with ZipFile(backup_path) as archive:
            names = set(archive.namelist())
        assert "uploads/attachments/datasheet.txt" in names

        listed = client.get("/api/backups")
        assert listed.status_code == 200
        assert any(item["backup_id"] == backup["backup_id"] for item in listed.json()["data"]["backups"])

        downloaded = client.get(f"/api/backups/{backup['backup_id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"] == "application/zip"
        assert downloaded.content

        upload_file.unlink()
        restored = client.post(f"/api/backups/{backup['backup_id']}/restore")
        assert restored.status_code == 200
        assert restored.json()["data"]["backup_id"] == backup["backup_id"]
        assert upload_file.read_text(encoding="utf-8") == "datasheet-v1"
        assert any(path.name.startswith("snapshot-") for path in settings.backup_dir.glob("snapshot-*.zip"))
    finally:
        settings.upload_dir = old_upload_dir
        settings.backup_dir = old_backup_dir
        create_schema()
        with SessionLocal() as db:
            init_default_data(db)
