import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["API_TOKEN_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


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
    assert use_response.json()["data"]["quantity"] == "0.300"

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
