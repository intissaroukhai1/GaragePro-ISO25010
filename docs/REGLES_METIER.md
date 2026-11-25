# Règles métier documentées

| Code | Règle | Application |
|---|---|---|
| BR-01 | Immatriculation unique | Contrainte `vehicles.plate UNIQUE` et 409 |
| BR-02 | Un mécanicien ne peut avoir deux rendez-vous planifiés se chevauchant | `check_schedule`; réponse 409 |
| BR-03 | Une intervention en réparation requiert un diagnostic | `PATCH /interventions/{id}/status`; réponse 422 |
| BR-04 | Pas de consommation de pièces si stock insuffisant | `POST /interventions/{id}/parts`; réponse 409 |
| BR-05 | Les transitions de statut suivent le graphe autorisé | Dictionnaire `TRANSITIONS`; réponse 409 |
| BR-06 | Le client ne peut accéder qu'à ses propres véhicules, réservations, interventions et factures | `owned_vehicle`, filtres SQL côté API |
| BR-07 | La consommation de pièces et l'audit sont transactionnels | `with_for_update()` sous PostgreSQL et `db.commit()` atomique |
| BR-08 | On ne crée une facture qu'après la fin de la réparation | Statut `COMPLETED`; réponse 409 |
| BR-09 | Une seule facture peut être associée à une intervention | Clé `UNIQUE` sur `invoices.intervention_id` |
| BR-10 | Impossible de supprimer une ressource référencée (véhicule, mécanicien, pièce) | Contrôles de dépendance et réponse 409 |

## Workflow

```text
REQUESTED → DIAGNOSIS → REPAIR → COMPLETED
      └───────────→ CANCELLED
                  (aussi depuis DIAGNOSIS)
```

Note : les règles sont **implémentées dans le code** mais non couvertes par des suites de tests dans ce ZIP. Les tests pourront être ajoutés plus tard selon le cahier des charges.
