"""Isolated test database. NEVER connects to the production Docker PostgreSQL database."""

import os
import sys
import tempfile
from pathlib import Path

# MUST be configured before importing the GaragePro application.
_TEMP_DIR = tempfile.TemporaryDirectory(prefix="garagepro_pytest_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_TEMP_DIR.name) / "garagepro_test.db")
os.environ["SEED_DEMO"] = "false"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from app import main as gp


@pytest.fixture
def environment():
    gp.Base.metadata.drop_all(gp.engine)
    gp.Base.metadata.create_all(gp.engine)

    with gp.SessionLocal() as db:
        users = {}
        for role, email in [
            ("ADMIN", "admin@example.com"),
            ("MECANICIEN", "mechanic@example.com"),
            ("CLIENT", "client@example.com"),
        ]:
            user = gp.User(
                name=role,
                email=email,
                password_hash=gp.hash_password("TestPass123!"),
                role=role,
            )
            db.add(user)
            db.flush()
            users[role] = user.id

        mechanic = gp.Mechanic(user_id=users["MECANICIEN"], specialty="Général")
        db.add(mechanic)
        db.flush()
        mechanic_id = mechanic.id
        db.commit()

    try:
        with TestClient(gp.app) as client:
            tokens = {}
            for role, email in [
                ("ADMIN", "admin@example.com"),
                ("MECANICIEN", "mechanic@example.com"),
                ("CLIENT", "client@example.com"),
            ]:
                response = client.post(
                    "/api/auth/login",
                    json={"email": email, "password": "TestPass123!"},
                )
                assert response.status_code == 200, response.text
                tokens[role] = {
                    "Authorization": "Bearer " + response.json()["access_token"]
                }
            yield client, tokens, users, mechanic_id
    finally:
        # After TestClient exits, remove tables and close SQLAlchemy's pooled connections.
        try:
            gp.Base.metadata.drop_all(gp.engine)
        finally:
            gp.engine.dispose()


@pytest.fixture
def scenario(environment):
    client, tokens, users, mechanic_id = environment
    vehicle = client.post(
        "/api/vehicles",
        headers=tokens["CLIENT"],
        json={
            "plate": "200 TUN 1234",
            "brand": "VW",
            "model": "Golf",
            "year": 2011,
        },
    )
    assert vehicle.status_code == 201, vehicle.text
    vehicle_id = vehicle.json()["id"]

    part = client.post(
        "/api/parts",
        headers=tokens["ADMIN"],
        json={
            "sku": "FIL-001",
            "name": "Filtre huile",
            "stock": 20,
            "unit_price": "25.00",
        },
    )
    assert part.status_code == 201, part.text
    return client, tokens, users, mechanic_id, vehicle_id, part.json()["id"]


def pytest_unconfigure(config):
    """Release the database file on Windows after pytest has finished reporting."""
    gp.engine.dispose()
    _TEMP_DIR.cleanup()
