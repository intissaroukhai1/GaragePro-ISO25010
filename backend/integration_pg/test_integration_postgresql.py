"""Tests d'integration: API FastAPI <-> vraie base PostgreSQL temporaire.

Les assertions lisent les lignes dans PostgreSQL (sessions SQLAlchemy independantes),
ce que les tests API de l'etape 1 avec SQLite ne prouvaient pas.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select, func, text
from app import main as gp


def must(response, status):
    assert response.status_code == status, f"HTTP {response.status_code}, attendu {status}: {response.text}"
    return response.json()


def vehicle(env, *, admin=False, plate="200 TUN 1234"):
    c, h = env["client"], env["headers"]
    payload = {"plate": plate, "brand": "VW", "model": "Golf", "year": 2011}
    if admin:
        payload["owner_id"] = env["users"]["CLIENT"]
    return must(c.post("/api/vehicles", headers=h["ADMIN" if admin else "CLIENT"], json=payload), 201)["id"]


def appointment(env, vehicle_id, *, start="2030-04-02T09:00:00+00:00", end="2030-04-02T10:00:00+00:00"):
    c, h = env["client"], env["headers"]
    data = {"vehicle_id": vehicle_id, "mechanic_id": env["mechanics"]["MECANICIEN"],
            "starts_at": start, "ends_at": end, "reason": "Vidange et revision"}
    return must(c.post("/api/appointments", headers=h["CLIENT"], json=data), 201)["id"]


def intervention_ready(env, vehicle_id):
    c, h = env["client"], env["headers"]
    i = must(c.post("/api/interventions", headers=h["ADMIN"], json={
        "vehicle_id": vehicle_id,
        "mechanic_id": env["mechanics"]["MECANICIEN"],
        "description": "Vidange + filtre a huile", "labor_cost": "40.00",
    }), 201)["id"]
    must(c.patch(f"/api/interventions/{i}/status", headers=h["MECANICIEN"],
                 json={"status": "DIAGNOSIS"}), 200)
    must(c.patch(f"/api/interventions/{i}/status", headers=h["MECANICIEN"],
                 json={"status": "REPAIR", "diagnosis": "Filtre encrasse, huile usagee"}), 200)
    return i


def part(env, sku, stock, price):
    c, h = env["client"], env["headers"]
    return must(c.post("/api/parts", headers=h["ADMIN"], json={
        "sku": sku, "name": "Piece " + sku,
        "stock": stock, "unit_price": str(price)
    }), 201)["id"]


def test_pg01_connexion_reelle_postgresql(pg_environment):
    """PG-01: moteur et base physiquement PostgreSQL 16."""
    with gp.SessionLocal() as db:
        assert db.bind.dialect.name == "postgresql"
        assert db.scalar(text("SELECT current_database()")) == "garagepro_integration_test"
        assert db.scalar(text("SHOW server_version_num"))[:2] == "16"


def test_pg02_crud_vehicule_et_audit_persistants(pg_environment):
    """PG-02: les CRUD et l'audit sont reellement persistes en PostgreSQL."""
    env = pg_environment
    c, h = env["client"], env["headers"]
    vid = vehicle(env, admin=True)
    with gp.SessionLocal() as db:
        stored = db.get(gp.Vehicle, vid)
        assert stored.plate == "200 TUN 1234"
        assert stored.owner_id == env["users"]["CLIENT"]
    # Les vehicules saisis par ADMIN sont visibles par le mecanicien.
    visible = must(c.get("/api/vehicles", headers=h["MECANICIEN"]), 200)
    assert any(row["id"] == vid for row in visible)
    must(c.put(f"/api/vehicles/{vid}", headers=h["ADMIN"], json={
        "owner_id": env["users"]["CLIENT"], "plate": "200 TUN 5678",
        "brand": "Renault", "model": "Clio", "year": 2017,
    }), 200)
    with gp.SessionLocal() as db:
        assert db.get(gp.Vehicle, vid).plate == "200 TUN 5678"
    must(c.delete(f"/api/vehicles/{vid}", headers=h["ADMIN"]), 200)
    with gp.SessionLocal() as db:
        assert db.get(gp.Vehicle, vid) is None
        actions = db.scalars(select(gp.AuditLog.action).where(
            gp.AuditLog.resource == "vehicles", gp.AuditLog.resource_id == vid
        )).all()
        assert {"CREATE", "UPDATE", "DELETE"} <= set(actions)


def test_pg03_crud_rendezvous_client_persistant(pg_environment):
    """PG-03: le client cree, modifie et supprime son rendez-vous en attente."""
    env = pg_environment
    c, h = env["client"], env["headers"]
    vid = vehicle(env)
    aid = appointment(env, vid)
    with gp.SessionLocal() as db:
        assert db.get(gp.Appointment, aid).status == "PENDING"
    updated = must(c.put(f"/api/appointments/{aid}", headers=h["CLIENT"], json={
        "vehicle_id": vid, "mechanic_id": env["mechanics"]["MECANICIEN"],
        "starts_at": "2030-04-03T11:00:00+00:00",
        "ends_at": "2030-04-03T12:00:00+00:00",
        "reason": "Revision du vehicule",
    }), 200)
    assert updated["reason"] == "Revision du vehicule"
    with gp.SessionLocal() as db:
        assert db.get(gp.Appointment, aid).reason == "Revision du vehicule"
    must(c.delete(f"/api/appointments/{aid}", headers=h["CLIENT"]), 200)
    with gp.SessionLocal() as db:
        assert db.get(gp.Appointment, aid) is None


def test_pg04_acceptation_et_visibilite_du_vehicule_client(pg_environment):
    """PG-04: acceptation mec -> PLANNED et droit de voir le vehicule client."""
    env = pg_environment
    c, h = env["client"], env["headers"]
    vid = vehicle(env)
    aid = appointment(env, vid)
    before = must(c.get("/api/vehicles", headers=h["MECANICIEN"]), 200)
    assert not any(row["id"] == vid for row in before)
    assert must(c.patch(f"/api/appointments/{aid}/accept", headers=h["MECANICIEN"]), 200)["status"] == "PLANNED"
    after = must(c.get("/api/vehicles", headers=h["MECANICIEN"]), 200)
    assert any(row["id"] == vid for row in after)
    client_appointments = must(c.get("/api/appointments", headers=h["CLIENT"]), 200)
    assert any(row["id"] == aid and row["status"] == "PLANNED" for row in client_appointments)
    with gp.SessionLocal() as db:
        assert db.get(gp.Appointment, aid).status == "PLANNED"
    # Un rendez-vous confirme n'est plus modifiable par le client.
    forbidden = c.put(f"/api/appointments/{aid}", headers=h["CLIENT"], json={
        "vehicle_id": vid, "mechanic_id": env["mechanics"]["MECANICIEN"],
        "starts_at": "2030-04-04T11:00:00+00:00",
        "ends_at": "2030-04-04T12:00:00+00:00", "reason": "Autre motif",
    })
    must(forbidden, 409)


def test_pg05_refus_mecanicien_non_affecte_et_conflit_horaire(pg_environment):
    """PG-05: autorisations PostgreSQL et conflit de planning."""
    env = pg_environment
    c, h = env["client"], env["headers"]
    vid = vehicle(env)
    first = appointment(env, vid)
    must(c.patch(f"/api/appointments/{first}/accept", headers=h["MECANICIEN2"]), 403)
    must(c.patch(f"/api/appointments/{first}/accept", headers=h["MECANICIEN"]), 200)
    second = appointment(env, vid)  # meme plage horaire
    must(c.patch(f"/api/appointments/{second}/accept", headers=h["MECANICIEN"]), 409)
    with gp.SessionLocal() as db:
        assert db.get(gp.Appointment, first).status == "PLANNED"
        assert db.get(gp.Appointment, second).status == "PENDING"


def test_pg06_intervention_creee_admin_et_reparation_mecanicien(pg_environment):
    """PG-06: controle d'acces + transitions et rapport en BDD."""
    env = pg_environment
    c, h = env["client"], env["headers"]
    vid = vehicle(env)
    data = {"vehicle_id": vid, "mechanic_id": env["mechanics"]["MECANICIEN"],
            "description": "Vidange du vehicule", "labor_cost": "40.00"}
    must(c.post("/api/interventions", headers=h["CLIENT"], json=data), 403)
    iid = must(c.post("/api/interventions", headers=h["ADMIN"], json=data), 201)["id"]
    must(c.patch(f"/api/interventions/{iid}/status", headers=h["MECANICIEN"],
                 json={"status": "DIAGNOSIS"}), 200)
    must(c.patch(f"/api/interventions/{iid}/status", headers=h["MECANICIEN"],
                 json={"status": "REPAIR", "diagnosis": "Filtre bouche"}), 200)
    must(c.put(f"/api/interventions/{iid}/report", headers=h["MECANICIEN"], json={
        "work_done": "Vidange moteur et controle du filtre effectues.",
        "observations": "Vehicule operationnel.",
    }), 200)
    with gp.SessionLocal() as db:
        work = db.scalar(select(gp.WorkReport).where(gp.WorkReport.intervention_id == iid))
        assert work is not None and work.mechanic_id == env["mechanics"]["MECANICIEN"]
    must(c.patch(f"/api/interventions/{iid}/status", headers=h["MECANICIEN"],
                 json={"status": "COMPLETED"}), 200)
    with gp.SessionLocal() as db:
        assert db.get(gp.Intervention, iid).status == "COMPLETED"


def test_pg07_stock_multiple_atomique_et_alertes(pg_environment):
    """PG-07: la base de donnees assure deductions et absence de demi-commit."""
    env = pg_environment
    c, h = env["client"], env["headers"]
    vid = vehicle(env)
    iid = intervention_ready(env, vid)
    p1 = part(env, "FIL-PG", 7, "25.00")
    p2 = part(env, "HUI-PG", 2, "95.00")
    rows = must(c.post(f"/api/interventions/{iid}/parts/bulk", headers=h["MECANICIEN"],
             json={"items": [{"part_id": p1, "quantity": 2}, {"part_id": p2, "quantity": 1}]}), 201)
    assert len(rows) == 2
    with gp.SessionLocal() as db:
        assert db.get(gp.Part, p1).stock == 5
        assert db.get(gp.Part, p2).stock == 1
        assert db.scalar(select(func.count()).select_from(gp.PartUsage)) == 2
    dashboard = must(c.get("/api/dashboard", headers=h["ADMIN"]), 200)
    assert dashboard["parts_low_stock"] == 2
    assert {a["sku"] for a in dashboard["stock_alerts"]} == {"FIL-PG", "HUI-PG"}
    # Une nouvelle demande groupée invalide ne doit modifier AUCUN stock.
    p3 = part(env, "BAT-PG", 6, "180.00")
    p4 = part(env, "FRE-PG", 1, "80.00")
    must(c.post(f"/api/interventions/{iid}/parts/bulk", headers=h["MECANICIEN"], json={
        "items": [{"part_id": p3, "quantity": 2}, {"part_id": p4, "quantity": 2}]
    }), 409)
    with gp.SessionLocal() as db:
        assert db.get(gp.Part, p3).stock == 6
        assert db.get(gp.Part, p4).stock == 1
        assert db.scalar(select(func.count()).select_from(gp.PartUsage)) == 2


def test_pg08_facturation_paiement_client_et_audit(pg_environment):
    """PG-08: montant facture = main d'oeuvre + pieces, persistant en BDD."""
    env = pg_environment
    c, h = env["client"], env["headers"]
    vid = vehicle(env)
    iid = intervention_ready(env, vid)
    pid = part(env, "FIL-PG", 8, "25.00")
    must(c.post(f"/api/interventions/{iid}/parts/bulk", headers=h["MECANICIEN"],
         json={"items": [{"part_id": pid, "quantity": 2}]}), 201)
    must(c.patch(f"/api/interventions/{iid}/status", headers=h["MECANICIEN"],
                 json={"status": "COMPLETED"}), 200)
    must(c.post(f"/api/invoices/{iid}", headers=h["CLIENT"]), 403)
    inv = must(c.post(f"/api/invoices/{iid}", headers=h["ADMIN"]), 201)
    assert Decimal(inv["amount"]) == Decimal("90.00")  # 40 + 2 x 25
    with gp.SessionLocal() as db:
        persisted = db.get(gp.Invoice, inv["id"])
        assert persisted is not None and persisted.amount == Decimal("90.00")
    client_invoices = must(c.get("/api/invoices", headers=h["CLIENT"]), 200)
    assert any(row["id"] == inv["id"] for row in client_invoices)
    paid = must(c.patch(f"/api/invoices/{inv['id']}", headers=h["ADMIN"], json={"status": "PAID"}), 200)
    assert paid["status"] == "PAID"
    must(c.post(f"/api/invoices/{iid}", headers=h["ADMIN"]), 409)
    with gp.SessionLocal() as db:
        assert db.get(gp.Invoice, inv["id"]).status == "PAID"
        actions = db.scalars(select(gp.AuditLog.action).where(gp.AuditLog.resource == "invoices")).all()
        assert "CREATE" in actions and "MARK_PAID" in actions
