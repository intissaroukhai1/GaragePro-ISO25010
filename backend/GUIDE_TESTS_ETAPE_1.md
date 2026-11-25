# GaragePro — Étape 1 : tests unitaires et API isolés

Ces tests proviennent du code réellement fourni dans cette archive. Ils n'accèdent **jamais** à la base Docker PostgreSQL : `conftest.py` force une base SQLite temporaire **avant** l'import de `app.main`.

## Windows CMD depuis le dossier du projet

```cmd
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-test.txt
.venv\Scripts\python -m pytest tests -v
.venv\Scripts\python -m pytest tests --cov=app --cov-report=term-missing --cov-report=html:../reports/coverage-html --junitxml=../reports/pytest-results.xml
```

Le dossier `reports/` est créé dans le ZIP. Ouvrir `reports/coverage-html/index.html` pour la couverture.

**Attention** : les tests API utilisent SQLite et constituent une première vérification locale. Les comportements spécifiques PostgreSQL (verrous, concurrence, contraintes sous charge) doivent ensuite être vérifiés dans une base PostgreSQL de test distincte. Ne jamais lancer des tests destructifs sur la base du garage.

## Étapes suivantes

1. Tests d'intégration PostgreSQL isolée ; 2. Tests contractuels API/Postman ; 3. tests E2E Playwright ; 4. performance Locust ; 5. fiabilité ; 6. SAST ; 7. SCA ; 8. DAST ; 9. qualité et couverture ; 10. compatibilité ; 11. portabilité ; 12. matrices et rapport ISO.
