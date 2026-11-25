"""GaragePro ISO 25010 - charge locale sur environnement E2E isolé.

Ne contient aucun appel d'écriture. Le contrôle de cible est aussi effectué par
les scripts Windows avant l'exécution. Ne jamais pointer vers la production.
"""
from locust import HttpUser, task, between


class GarageProReadOnlyUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://127.0.0.1:18082"

    @task
    def health(self):
        with self.client.get("/api/health", name="GET /api/health", catch_response=True, timeout=10) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code} au lieu de 200")
                return
            try:
                body = response.json()
            except ValueError:
                response.failure("Réponse JSON invalide")
                return
            if body.get("status") != "ok" or body.get("service") != "garagepro":
                response.failure("Réponse inattendue : service/status incorrect")
            else:
                response.success()
