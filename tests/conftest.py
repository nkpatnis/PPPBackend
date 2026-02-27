import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# In-memory SQLite — isolated, no MySQL required
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables before every test for a clean slate."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db(reset_db):
    session = _TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers re-used across multiple test modules
# ---------------------------------------------------------------------------

def register_and_login(client, email="user@test.com", password="TestPass123"):
    """Register (if not exists) and return auth headers for the user."""
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def create_material(client, headers, name="Flour", unit="kg", price_amount=50, price_quantity=1):
    r = client.post(
        "/api/v1/materials",
        json={"name": name, "unit": unit, "price_amount": price_amount, "price_quantity": price_quantity},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def product_payload(mat1_id, mat2_id):
    return {
        "product_name": "Chocolate Cake",
        "entries": [
            {"material_id": mat1_id, "quantity_str": "2"},
            {"material_id": mat2_id, "quantity_str": "0.5"},
        ],
        "batch_output_quantity": 10,
        "packaging_cost_per_unit": 5,
        "margin_percentage": 30,
        "result": {
            "total_material_cost": 120.0,
            "cost_per_unit": 12.0,
            "final_cost_per_unit": 17.0,
            "selling_price": 22.1,
        },
        "material_snapshots": [
            {
                "material_id": mat1_id,
                "name": "Flour",
                "unit": "kg",
                "price_amount": 50,
                "price_quantity": 1,
                "market_price_per_unit": 50,
                "quantity_used": 2,
                "line_cost": 100,
            },
            {
                "material_id": mat2_id,
                "name": "Sugar",
                "unit": "kg",
                "price_amount": 80,
                "price_quantity": 2,
                "market_price_per_unit": 40,
                "quantity_used": 0.5,
                "line_cost": 20,
            },
        ],
    }
