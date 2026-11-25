# ISO/IEC 25010 — Plan de vérification à compléter

Ce ZIP contient l'application et **aucun test**, conformément à la demande. Le cahier des charges impose des résultats réels pour chacune des huit caractéristiques et interdit toute preuve inventée.

| Caractéristique | Vérification à ajouter dans une phase ultérieure | État actuel |
|---|---|---|
| Aptitude fonctionnelle | Pytest unitaires, intégration, Postman/Newman et Playwright E2E | Non exécuté |
| Efficacité de performance | Locust, 20 utilisateurs simultanés, temps et débit | Non exécuté |
| Compatibilité | Playwright Chromium et Firefox | Non exécuté |
| Facilité d'utilisation | Recette utilisateur et vérification d'accessibilité | Non exécuté |
| Fiabilité | Rollback, double consommation de stock, reprise après panne | Non exécuté |
| Sécurité | RBAC, Bandit SAST, pip-audit SCA, OWASP ZAP DAST | Non exécuté |
| Maintenabilité | Ruff, couverture et analyse de complexité | Non exécuté |
| Portabilité | Construction Docker et installation sur autre machine | Non exécuté |

## Livrables restant à produire pour la soutenance

- Suites de tests exécutables par couche.
- Rapport réel de couverture, résultats et journaux d'outils.
- Matrice de traçabilité renseignée avec les noms exacts des tests et leurs résultats.
- Rapport de conformité qualité avec une preuve par caractéristique.
- Historique Git de travail réel.
- Démonstration live de l'application et d'au moins deux couches de tests.

**Rappel :** l'implémentation de fonctions métier ne vaut pas certification de conformité ISO 25010.
