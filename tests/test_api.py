"""
End-to-end unit tests for the PPPBackend API.

Covers:
  - Auth  (register, login, duplicate, wrong password, unauthorised)
  - Materials CRUD + bulk delete + search
  - Products CRUD + bulk delete + search
  - Bulk import (materials, products, duplicates, unknown-material error)
  - User isolation (user A cannot read/write user B's data)
"""

import pytest

from tests.conftest import (
    create_material,
    product_payload,
    register_and_login,
)


# ===========================================================================
# Auth
# ===========================================================================


class TestAuth:
    def test_register_success(self, client):
        r = client.post(
            "/api/v1/auth/register",
            json={"email": "a@test.com", "password": "Pass123", "full_name": "Alice"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "a@test.com"
        assert data["full_name"] == "Alice"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "password" not in data

    def test_register_duplicate_email(self, client):
        payload = {"email": "dup@test.com", "password": "Pass123"}
        client.post("/api/v1/auth/register", json=payload)
        r = client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"].lower()

    def test_login_success(self, client):
        client.post(
            "/api/v1/auth/register",
            json={"email": "b@test.com", "password": "Pass123"},
        )
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "b@test.com", "password": "Pass123"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        client.post(
            "/api/v1/auth/register",
            json={"email": "c@test.com", "password": "Correct1"},
        )
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "c@test.com", "password": "Wrong999"},
        )
        assert r.status_code == 401

    def test_login_unknown_email(self, client):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "Pass123"},
        )
        assert r.status_code == 401

    def test_protected_endpoint_without_token(self, client):
        r = client.get("/api/v1/materials")
        assert r.status_code == 401

    def test_protected_endpoint_invalid_token(self, client):
        r = client.get(
            "/api/v1/materials",
            headers={"Authorization": "Bearer not.a.real.token"},
        )
        assert r.status_code == 401


# ===========================================================================
# Materials
# ===========================================================================


class TestMaterials:
    def test_create_material_derives_market_price(self, client):
        h = register_and_login(client)
        r = client.post(
            "/api/v1/materials",
            json={"name": "Sugar", "unit": "kg", "price_amount": 80, "price_quantity": 2},
            headers=h,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Sugar"
        assert data["unit"] == "kg"
        assert data["price_amount"] == 80.0
        assert data["price_quantity"] == 2.0
        assert data["market_price_per_unit"] == 40.0  # 80 / 2

    def test_create_material_unit_price(self, client):
        h = register_and_login(client)
        r = client.post(
            "/api/v1/materials",
            json={"name": "Butter", "unit": "kg", "price_amount": 200, "price_quantity": 1},
            headers=h,
        )
        assert r.status_code == 201
        assert r.json()["market_price_per_unit"] == 200.0

    def test_list_materials_empty(self, client):
        h = register_and_login(client)
        r = client.get("/api/v1/materials", headers=h)
        assert r.status_code == 200
        assert r.json() == []

    def test_list_materials_returns_all(self, client):
        h = register_and_login(client)
        create_material(client, h, name="Flour")
        create_material(client, h, name="Sugar", price_amount=80, price_quantity=2)
        r = client.get("/api/v1/materials", headers=h)
        assert r.status_code == 200
        names = [m["name"] for m in r.json()]
        assert "Flour" in names
        assert "Sugar" in names

    def test_list_materials_search(self, client):
        h = register_and_login(client)
        create_material(client, h, name="Flour")
        create_material(client, h, name="Sugar", price_amount=80, price_quantity=2)
        r = client.get("/api/v1/materials?search=sug", headers=h)
        assert r.status_code == 200
        results = r.json()
        assert len(results) == 1
        assert results[0]["name"] == "Sugar"

    def test_list_materials_search_case_insensitive(self, client):
        h = register_and_login(client)
        create_material(client, h, name="Flour")
        r = client.get("/api/v1/materials?search=FLOUR", headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_update_material_price_recalculates_market_price(self, client):
        h = register_and_login(client)
        mat = create_material(client, h, name="Flour", price_amount=50, price_quantity=1)
        r = client.put(
            f"/api/v1/materials/{mat['id']}",
            json={"price_amount": 60},
            headers=h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["price_amount"] == 60.0
        assert data["market_price_per_unit"] == 60.0  # 60 / 1

    def test_update_material_quantity_recalculates_market_price(self, client):
        h = register_and_login(client)
        mat = create_material(client, h, name="Flour", price_amount=100, price_quantity=1)
        r = client.put(
            f"/api/v1/materials/{mat['id']}",
            json={"price_quantity": 2},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["market_price_per_unit"] == 50.0  # 100 / 2

    def test_update_material_name(self, client):
        h = register_and_login(client)
        mat = create_material(client, h, name="Old Name")
        r = client.put(
            f"/api/v1/materials/{mat['id']}",
            json={"name": "New Name"},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_update_material_not_found(self, client):
        h = register_and_login(client)
        r = client.put("/api/v1/materials/9999", json={"name": "X"}, headers=h)
        assert r.status_code == 404

    def test_delete_single_material(self, client):
        h = register_and_login(client)
        mat = create_material(client, h)
        r = client.delete(f"/api/v1/materials/{mat['id']}", headers=h)
        assert r.status_code == 204
        # Confirm gone
        listed = client.get("/api/v1/materials", headers=h).json()
        assert all(m["id"] != mat["id"] for m in listed)

    def test_delete_single_material_not_found(self, client):
        h = register_and_login(client)
        r = client.delete("/api/v1/materials/9999", headers=h)
        assert r.status_code == 404

    def test_delete_selected_materials(self, client):
        h = register_and_login(client)
        m1 = create_material(client, h, name="Flour")
        m2 = create_material(client, h, name="Sugar", price_amount=80, price_quantity=2)
        m3 = create_material(client, h, name="Butter", price_amount=200, price_quantity=1)
        r = client.delete(
            f"/api/v1/materials?ids={m1['id']}&ids={m2['id']}",
            headers=h,
        )
        assert r.status_code == 204
        remaining = [m["name"] for m in client.get("/api/v1/materials", headers=h).json()]
        assert remaining == ["Butter"]

    def test_delete_all_materials(self, client):
        h = register_and_login(client)
        create_material(client, h, name="Flour")
        create_material(client, h, name="Sugar", price_amount=80, price_quantity=2)
        r = client.delete("/api/v1/materials", headers=h)
        assert r.status_code == 204
        assert client.get("/api/v1/materials", headers=h).json() == []


# ===========================================================================
# Products
# ===========================================================================


class TestProducts:

    def _setup(self, client):
        """Register user and create two materials; return (headers, mat1, mat2)."""
        h = register_and_login(client)
        m1 = create_material(client, h, name="Flour", price_amount=50, price_quantity=1)
        m2 = create_material(client, h, name="Sugar", price_amount=80, price_quantity=2)
        return h, m1, m2

    def test_create_product_structure(self, client):
        h, m1, m2 = self._setup(client)
        r = client.post("/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h)
        assert r.status_code == 201
        data = r.json()
        assert data["product_name"] == "Chocolate Cake"
        assert data["batch_output_quantity"] == 10.0
        assert data["packaging_cost_per_unit"] == 5.0
        assert data["margin_percentage"] == 30.0
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_product_result_nested(self, client):
        h, m1, m2 = self._setup(client)
        r = client.post("/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h)
        result = r.json()["result"]
        assert result["total_material_cost"] == 120.0
        assert result["cost_per_unit"] == 12.0
        assert result["final_cost_per_unit"] == 17.0
        assert result["selling_price"] == 22.1

    def test_create_product_entries(self, client):
        h, m1, m2 = self._setup(client)
        r = client.post("/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h)
        entries = r.json()["entries"]
        assert len(entries) == 2
        entry_mat_ids = {e["material_id"] for e in entries}
        assert m1["id"] in entry_mat_ids
        assert m2["id"] in entry_mat_ids

    def test_create_product_snapshots_frozen(self, client):
        h, m1, m2 = self._setup(client)
        r = client.post("/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h)
        snaps = r.json()["material_snapshots"]
        assert len(snaps) == 2
        flour_snap = next(s for s in snaps if s["name"] == "Flour")
        assert flour_snap["price_amount"] == 50.0
        assert flour_snap["market_price_per_unit"] == 50.0
        assert flour_snap["quantity_used"] == 2.0
        assert flour_snap["line_cost"] == 100.0

    def test_list_products_empty(self, client):
        h = register_and_login(client)
        r = client.get("/api/v1/products", headers=h)
        assert r.status_code == 200
        assert r.json() == []

    def test_list_products_returns_summary(self, client):
        h, m1, m2 = self._setup(client)
        client.post("/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h)
        r = client.get("/api/v1/products", headers=h)
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1
        item = items[0]
        # List view has summary fields only
        assert item["product_name"] == "Chocolate Cake"
        assert item["selling_price"] == 22.1
        assert item["final_cost_per_unit"] == 17.0
        assert "entries" not in item
        assert "material_snapshots" not in item

    def test_list_products_search(self, client):
        h, m1, m2 = self._setup(client)
        client.post("/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h)
        bread_payload = {
            "product_name": "Bread",
            "entries": [{"material_id": m1["id"], "quantity_str": "1"}],
            "batch_output_quantity": 20,
            "packaging_cost_per_unit": 2,
            "margin_percentage": 25,
            "result": {"total_material_cost": 50, "cost_per_unit": 2.5, "final_cost_per_unit": 4.5, "selling_price": 5.625},
            "material_snapshots": [{
                "material_id": m1["id"], "name": "Flour", "unit": "kg",
                "price_amount": 50, "price_quantity": 1, "market_price_per_unit": 50,
                "quantity_used": 1, "line_cost": 50,
            }],
        }
        client.post("/api/v1/products", json=bread_payload, headers=h)
        r = client.get("/api/v1/products?search=bread", headers=h)
        assert r.status_code == 200
        results = r.json()
        assert len(results) == 1
        assert results[0]["product_name"] == "Bread"

    def test_get_product_detail(self, client):
        h, m1, m2 = self._setup(client)
        created = client.post(
            "/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h
        ).json()
        r = client.get(f"/api/v1/products/{created['id']}", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == created["id"]
        assert len(data["entries"]) == 2
        assert len(data["material_snapshots"]) == 2
        assert "result" in data

    def test_get_product_not_found(self, client):
        h = register_and_login(client)
        r = client.get("/api/v1/products/9999", headers=h)
        assert r.status_code == 404

    def test_update_product_partial_margin(self, client):
        h, m1, m2 = self._setup(client)
        created = client.post(
            "/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h
        ).json()
        r = client.put(
            f"/api/v1/products/{created['id']}",
            json={
                "margin_percentage": 50,
                "result": {
                    "total_material_cost": 120,
                    "cost_per_unit": 12,
                    "final_cost_per_unit": 17,
                    "selling_price": 25.5,
                },
            },
            headers=h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["margin_percentage"] == 50.0
        assert data["result"]["selling_price"] == 25.5
        # unchanged fields stay
        assert data["product_name"] == "Chocolate Cake"

    def test_update_product_name(self, client):
        h, m1, m2 = self._setup(client)
        created = client.post(
            "/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h
        ).json()
        r = client.put(
            f"/api/v1/products/{created['id']}",
            json={"product_name": "Dark Chocolate Cake"},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["product_name"] == "Dark Chocolate Cake"

    def test_update_product_updated_at_changes(self, client):
        h, m1, m2 = self._setup(client)
        created = client.post(
            "/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h
        ).json()
        updated = client.put(
            f"/api/v1/products/{created['id']}",
            json={"product_name": "New Name"},
            headers=h,
        ).json()
        # updated_at must be >= created_at
        assert updated["updated_at"] >= created["created_at"]

    def test_update_product_not_found(self, client):
        h = register_and_login(client)
        r = client.put("/api/v1/products/9999", json={"product_name": "X"}, headers=h)
        assert r.status_code == 404

    def test_delete_single_product(self, client):
        h, m1, m2 = self._setup(client)
        created = client.post(
            "/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h
        ).json()
        r = client.delete(f"/api/v1/products/{created['id']}", headers=h)
        assert r.status_code == 204
        assert client.get(f"/api/v1/products/{created['id']}", headers=h).status_code == 404

    def test_delete_single_product_not_found(self, client):
        h = register_and_login(client)
        r = client.delete("/api/v1/products/9999", headers=h)
        assert r.status_code == 404

    def test_delete_selected_products(self, client):
        h, m1, m2 = self._setup(client)
        p1 = client.post(
            "/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h
        ).json()
        bread = {
            "product_name": "Bread",
            "entries": [{"material_id": m1["id"], "quantity_str": "1"}],
            "batch_output_quantity": 20,
            "packaging_cost_per_unit": 2,
            "margin_percentage": 25,
            "result": {"total_material_cost": 50, "cost_per_unit": 2.5, "final_cost_per_unit": 4.5, "selling_price": 5.625},
            "material_snapshots": [{
                "material_id": m1["id"], "name": "Flour", "unit": "kg",
                "price_amount": 50, "price_quantity": 1, "market_price_per_unit": 50,
                "quantity_used": 1, "line_cost": 50,
            }],
        }
        p2 = client.post("/api/v1/products", json=bread, headers=h).json()
        r = client.delete(f"/api/v1/products?ids={p1['id']}", headers=h)
        assert r.status_code == 204
        remaining = [p["product_name"] for p in client.get("/api/v1/products", headers=h).json()]
        assert remaining == ["Bread"]

    def test_delete_all_products(self, client):
        h, m1, m2 = self._setup(client)
        client.post("/api/v1/products", json=product_payload(m1["id"], m2["id"]), headers=h)
        r = client.delete("/api/v1/products", headers=h)
        assert r.status_code == 204
        assert client.get("/api/v1/products", headers=h).json() == []


# ===========================================================================
# Bulk Import
# ===========================================================================


class TestBulkImport:

    def test_import_new_materials(self, client):
        h = register_and_login(client)
        r = client.post(
            "/api/v1/import",
            json={
                "materials": [
                    {"name": "Flour", "unit": "kg", "price_amount": 50, "price_quantity": 1},
                    {"name": "Sugar", "unit": "kg", "price_amount": 80, "price_quantity": 2},
                ],
                "product_lines": [],
            },
            headers=h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["materials_added"] == 2
        assert data["materials_duplicated"] == 0
        assert data["products_added"] == 0
        assert data["errors"] == []
        # Verify in DB
        mats = client.get("/api/v1/materials", headers=h).json()
        assert len(mats) == 2

    def test_import_skips_duplicate_materials_case_insensitive(self, client):
        h = register_and_login(client)
        # Pre-create Flour
        create_material(client, h, name="Flour", price_amount=50, price_quantity=1)
        r = client.post(
            "/api/v1/import",
            json={
                "materials": [
                    # "flour" lowercase should be detected as duplicate
                    {"name": "flour", "unit": "kg", "price_amount": 60, "price_quantity": 1},
                    {"name": "Butter", "unit": "kg", "price_amount": 200, "price_quantity": 1},
                ],
                "product_lines": [],
            },
            headers=h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["materials_added"] == 1
        assert data["materials_duplicated"] == 1
        # Original Flour price unchanged
        mats = {m["name"]: m for m in client.get("/api/v1/materials", headers=h).json()}
        assert mats["Flour"]["price_amount"] == 50.0

    def test_import_products_calculates_cost(self, client):
        h = register_and_login(client)
        # Pre-create materials
        create_material(client, h, name="Flour", price_amount=50, price_quantity=1)
        create_material(client, h, name="Butter", price_amount=200, price_quantity=1)
        r = client.post(
            "/api/v1/import",
            json={
                "materials": [],
                "product_lines": [
                    {
                        "product_name": "Croissant",
                        "batch_output_quantity": 10,
                        "packaging_cost_per_unit": 3,
                        "margin_percentage": 40,
                        "material_name": "Flour",
                        "quantity_used": 1,
                    },
                    {
                        "product_name": "Croissant",
                        "batch_output_quantity": 10,
                        "packaging_cost_per_unit": 3,
                        "margin_percentage": 40,
                        "material_name": "Butter",
                        "quantity_used": 0.2,
                    },
                ],
            },
            headers=h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["products_added"] == 1
        assert data["products_skipped"] == 0
        assert data["errors"] == []
        # Verify calculated values: total = 50*1 + 200*0.2 = 90
        products = client.get("/api/v1/products", headers=h).json()
        assert len(products) == 1
        croissant = products[0]
        assert croissant["product_name"] == "Croissant"
        # cost_per_unit = 90 / 10 = 9; final = 9 + 3 = 12; selling = 12 * 1.4 = 16.8
        assert croissant["final_cost_per_unit"] == pytest.approx(12.0)
        assert croissant["selling_price"] == pytest.approx(16.8)

    def test_import_products_unknown_material_reports_error(self, client):
        h = register_and_login(client)
        r = client.post(
            "/api/v1/import",
            json={
                "materials": [],
                "product_lines": [
                    {
                        "product_name": "Ghost Cake",
                        "batch_output_quantity": 5,
                        "packaging_cost_per_unit": 1,
                        "margin_percentage": 20,
                        "material_name": "NonExistentIngredient",
                        "quantity_used": 1,
                    }
                ],
            },
            headers=h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["products_skipped"] == 1
        assert data["products_added"] == 0
        assert len(data["errors"]) == 1
        assert data["errors"][0]["field"] == "material_name"

    def test_import_materials_and_products_together(self, client):
        h = register_and_login(client)
        r = client.post(
            "/api/v1/import",
            json={
                "materials": [
                    {"name": "Flour", "unit": "kg", "price_amount": 50, "price_quantity": 1},
                    {"name": "Flour", "unit": "kg", "price_amount": 50, "price_quantity": 1},  # dup within batch
                ],
                "product_lines": [
                    {
                        "product_name": "Bread",
                        "batch_output_quantity": 20,
                        "packaging_cost_per_unit": 2,
                        "margin_percentage": 25,
                        "material_name": "Flour",
                        "quantity_used": 1,
                    }
                ],
            },
            headers=h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["materials_added"] == 1
        assert data["materials_duplicated"] == 1
        assert data["products_added"] == 1
        assert data["errors"] == []

    def test_import_empty_request(self, client):
        h = register_and_login(client)
        r = client.post(
            "/api/v1/import",
            json={"materials": [], "product_lines": []},
            headers=h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["materials_added"] == 0
        assert data["products_added"] == 0

    def test_import_snapshots_use_current_material_price(self, client):
        """Snapshots in imported products should reflect live material prices at import time."""
        h = register_and_login(client)
        r = client.post(
            "/api/v1/import",
            json={
                "materials": [
                    {"name": "Flour", "unit": "kg", "price_amount": 50, "price_quantity": 1}
                ],
                "product_lines": [
                    {
                        "product_name": "Bread",
                        "batch_output_quantity": 10,
                        "packaging_cost_per_unit": 1,
                        "margin_percentage": 20,
                        "material_name": "Flour",
                        "quantity_used": 2,
                    }
                ],
            },
            headers=h,
        )
        assert r.status_code == 200
        prod = client.get("/api/v1/products", headers=h).json()[0]
        detail = client.get(f"/api/v1/products/{prod['id']}", headers=h).json()
        snap = detail["material_snapshots"][0]
        assert snap["name"] == "Flour"
        assert snap["price_amount"] == 50.0
        assert snap["quantity_used"] == 2.0
        assert snap["line_cost"] == pytest.approx(100.0)  # 50 * 2


# ===========================================================================
# User Isolation
# ===========================================================================


class TestUserIsolation:

    def test_materials_scoped_to_user(self, client):
        h_a = register_and_login(client, email="alice@test.com")
        h_b = register_and_login(client, email="bob@test.com")
        create_material(client, h_a, name="AliceFlour")
        create_material(client, h_b, name="BobSugar", price_amount=80, price_quantity=2)

        a_mats = [m["name"] for m in client.get("/api/v1/materials", headers=h_a).json()]
        b_mats = [m["name"] for m in client.get("/api/v1/materials", headers=h_b).json()]

        assert a_mats == ["AliceFlour"]
        assert b_mats == ["BobSugar"]

    def test_user_cannot_update_other_users_material(self, client):
        h_a = register_and_login(client, email="alice@test.com")
        h_b = register_and_login(client, email="bob@test.com")
        mat = create_material(client, h_a, name="AliceFlour")

        r = client.put(
            f"/api/v1/materials/{mat['id']}",
            json={"name": "Hacked"},
            headers=h_b,
        )
        assert r.status_code == 404

    def test_user_cannot_delete_other_users_material(self, client):
        h_a = register_and_login(client, email="alice@test.com")
        h_b = register_and_login(client, email="bob@test.com")
        mat = create_material(client, h_a, name="AliceFlour")

        r = client.delete(f"/api/v1/materials/{mat['id']}", headers=h_b)
        assert r.status_code == 404
        # Still exists for Alice
        assert len(client.get("/api/v1/materials", headers=h_a).json()) == 1

    def test_products_scoped_to_user(self, client):
        h_a = register_and_login(client, email="alice@test.com")
        h_b = register_and_login(client, email="bob@test.com")

        m_a = create_material(client, h_a, name="Flour")
        m_b = create_material(client, h_b, name="Sugar", price_amount=80, price_quantity=2)

        a_prod = product_payload(m_a["id"], m_a["id"])
        a_prod["product_name"] = "Alice Cake"
        a_prod["entries"] = [{"material_id": m_a["id"], "quantity_str": "2"}]
        a_prod["material_snapshots"] = [a_prod["material_snapshots"][0]]
        client.post("/api/v1/products", json=a_prod, headers=h_a)

        b_prod = product_payload(m_b["id"], m_b["id"])
        b_prod["product_name"] = "Bob Pie"
        b_prod["entries"] = [{"material_id": m_b["id"], "quantity_str": "0.5"}]
        b_prod["material_snapshots"] = [b_prod["material_snapshots"][1]]
        client.post("/api/v1/products", json=b_prod, headers=h_b)

        a_products = [p["product_name"] for p in client.get("/api/v1/products", headers=h_a).json()]
        b_products = [p["product_name"] for p in client.get("/api/v1/products", headers=h_b).json()]

        assert a_products == ["Alice Cake"]
        assert b_products == ["Bob Pie"]

    def test_user_cannot_read_other_users_product(self, client):
        h_a = register_and_login(client, email="alice@test.com")
        h_b = register_and_login(client, email="bob@test.com")
        m = create_material(client, h_a, name="Flour")
        payload = product_payload(m["id"], m["id"])
        payload["entries"] = [{"material_id": m["id"], "quantity_str": "2"}]
        payload["material_snapshots"] = [payload["material_snapshots"][0]]
        prod = client.post("/api/v1/products", json=payload, headers=h_a).json()

        r = client.get(f"/api/v1/products/{prod['id']}", headers=h_b)
        assert r.status_code == 404

    def test_user_cannot_delete_other_users_product(self, client):
        h_a = register_and_login(client, email="alice@test.com")
        h_b = register_and_login(client, email="bob@test.com")
        m = create_material(client, h_a, name="Flour")
        payload = product_payload(m["id"], m["id"])
        payload["entries"] = [{"material_id": m["id"], "quantity_str": "2"}]
        payload["material_snapshots"] = [payload["material_snapshots"][0]]
        prod = client.post("/api/v1/products", json=payload, headers=h_a).json()

        r = client.delete(f"/api/v1/products/{prod['id']}", headers=h_b)
        assert r.status_code == 404
        # Still exists for Alice
        assert len(client.get("/api/v1/products", headers=h_a).json()) == 1

    def test_import_scoped_to_user(self, client):
        h_a = register_and_login(client, email="alice@test.com")
        h_b = register_and_login(client, email="bob@test.com")
        client.post(
            "/api/v1/import",
            json={
                "materials": [
                    {"name": "Flour", "unit": "kg", "price_amount": 50, "price_quantity": 1}
                ],
                "product_lines": [],
            },
            headers=h_a,
        )
        # Bob should see no materials
        assert client.get("/api/v1/materials", headers=h_b).json() == []
