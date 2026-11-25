# GaragePro — Étape 5 : Performance avec Locust

## Objectif
Évaluer le temps de réponse, le débit et le taux d'échec des requêtes à l'API GaragePro, dans une **stack E2E locale isolée**. Le scénario initial mesure uniquement `GET /api/health` : il ne représente pas les performances de tous les parcours métier.

## Où extraire ?
À la **racine** du projet GaragePro (à côté de `backend/` et `frontend/`). Ne pas remplacer les fichiers existants : fusionner le dossier `tests/performance/` avec le dossier `tests/` déjà présent.

## Pré-requis
- Python 3.12 accessible par `py -3.12`.
- Environnement E2E de l'étape 4 fonctionnel : API sur `http://127.0.0.1:18082`, endpoint `/api/health`.
- Lancement sur votre PC seulement ; ne ciblez jamais une API de production sans autorisation.

## Commandes Windows CMD
```
cd /d G:\tests\GaragePro_Complet_Visibilite_Vehicules_CRUD_RDV_Statuts
curl.exe http://127.0.0.1:18082/api/health
call INSTALLER_ETAPE5.cmd
call TESTER_ETAPE5.cmd
start reports\performance\garagepro_smoke.html
```

Le test démarre 2 utilisateurs simulés, à raison de 1 nouvel utilisateur/s, pendant 30 secondes, avec un temps d'attente aléatoire entre 1 et 3 s. Uniquement des requêtes GET, aucune écriture.

## Mesures à relever pour le rapport
- Nombre total de requêtes.
- Requêtes échouées et pourcentage d'échec.
- Temps de réponse médian et p95 (95e percentile).
- Débit en requêtes/seconde.
- Contexte d'exécution : Windows, Docker, CPU/RAM si disponibles, date et configuration.

## Conformité ISO/IEC 25010
La caractéristique visée est l'efficience des performances (*performance efficiency*). La réussite d'un test sans erreurs ne garantit pas la performance acceptable : il faut définir des seuils mesurables adaptés au cahier des charges, puis comparer les observations.

## Interprétation et limites
`/api/health` est un parcours très léger. Il confirme la disponibilité et donne un indicateur préliminaire de latence ; il ne permet pas de conclure sur les requêtes authentifiées, les accès PostgreSQL, la gestion de stock ou les rendez-vous. Il faudra ensuite étendre les scénarios avec des endpoints connus, sur données de test uniquement.

## Ressources
Documentation officielle : https://docs.locust.io/en/stable/running-without-web-ui.html
Options : https://docs.locust.io/en/stable/config-options.html

Aucun résultat n'est fourni à l'avance : le rapport HTML et les CSV seront générés lors de l'exécution locale.
