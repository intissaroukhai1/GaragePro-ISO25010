"""GaragePro: tests d'integration sur PostgreSQL DE TEST, jamais sur la BDD production.

IMPORTANT: Executer ce dossier SEUL:
    py -3.12 -m pytest backend/integration_pg -v -p no:cacheprovider

Cette configuration n'a aucun point d'acces a la base Docker normale (port interne
5432 / conteneur 'db'). Elle se connecte seulement a 127.0.0.1:55432 et a la base
jetable 'garagepro_integration_test'. Les tables sont recreees entre les tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Initialise AVANT le premier import de app.main, car le moteur SQLAlchemy est global.
TEST_DSN = (
    "postgresql+psycopg://garagepro_test:garagepro_test_pwd"
    "@127.0.0.1:55432/garagepro_integration_test"
)

# Defend against an accidental combined run with the SQLite unit test suite.
if "app.main" in sys.modules:
    raise RuntimeError(
        "app.main est deja importe. Executez uniquement "
        "'pytest backend/integration_pg' (sans backend/tests)."
    )

os.environ["DATABASE_URL"] = TEST_DSN
os.environ["SEED_DEMO"] = "false"
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app import main as gp


def assert_test_database() -> None:
    """Hard fail avant toute creation/suppression si la BDD n'est pas celle de test."""
    url = gp.engine.url
    assert url.drivername == "postgresql+psycopg", "Moteur PostgreSQL requis"
    assert url.host == "127.0.0.1" and url.port == 55432, "Port test requis"
    assert url.database == "garagepro_integration_test", "Nom BDD test requis"
    assert url.username == "garagepro_test", "Utilisateur test requis"
    with gp.engine.connect() as connection:
        db_name = connection.execute(text("SELECT current_database() ")).scalar_one()
        db_user = connection.execute(text("SELECT current_user ")).scalar_one()
    assert (db_name, db_user) == (
        "garagepro_integration_test", "garagepro_test"
    ), "Connexion differente de la base de test: operation interrompue"


@pytest.fixture
def pg_environment():
    """Cree des donnees temporaires et les supprime entre les tests."""
    assert_test_database()
    gp.Base.metadata.drop_all(gp.engine)
    gp.Base.metadata.create_all(gp.engine)
    emails = {
        "ADMIN": "admin.integration@gmail.com",
        "MECANICIEN": "meca.integration@gmail.com",
        "MECANICIEN2": "meca2.integration@gmail.com",
        "CLIENT": "client.integration@gmail.com",
        "CLIENT2": "client2.integration@gmail.com",
    }
    roles = {k: ("MECANICIEN" if k.startswith("MECANICIEN") else "CLIENT" if k.startswith("CLIENT") else "ADMIN") for k in emails}
    with gp.SessionLocal() as db:
        ids = {}
        for key, email in emails.items():
            obj = gp.User(
                name=f"TEST {key}", email=email,
                password_hash=gp.hash_password("TestPass123!"), role=roles[key],
            )
            db.add(obj)
            db.flush()
            ids[key] = obj.id
        m1 = gp.Mechanic(user_id=ids["MECANICIEN"], specialty="Mecanique generale")
        m2 = gp.Mechanic(user_id=ids["MECANICIEN2"], specialty="Diagnostic")
        db.add_all([m1, m2]); db.flush()
        mechanics = {"MECANICIEN": m1.id, "MECANICIEN2": m2.id}
        db.commit()

    try:
        with TestClient(gp.app) as client:
            headers = {}
            for key, email in emails.items():
                response = client.post(
                    "/api/auth/login",
                    json={"email": email, "password": "TestPass123!"},
                )
                assert response.status_code == 200, response.text
                headers[key] = {
                    "Authorization": "Bearer " + response.json()["access_token"]
                }
            yield {"client": client, "headers": headers, "users": ids, "mechanics": mechanics}
    finally:
        # Verifie une deuxieme fois avant la destruction des tables temporaires.
        assert_test_database()
        gp.Base.metadata.drop_all(gp.engine)
        gp.engine.dispose()
