# Etape 4 - Tests E2E GaragePro - Playwright

## Objet
Selon le cahier des charges ISO/IEC 25010, les tests fonctionnels/E2E doivent démontrer les parcours réels dans l'interface. Ils contribuent à l'aptitude fonctionnelle et à la facilité d'utilisation. Ce pack propose aussi Chrome + Firefox pour préparer les tests de compatibilité, qui demandent des preuves séparées.

## Emplacement : IMPORTANT
Copiez **tous les fichiers à la racine du projet** où se trouvent `docker-compose.yml`, `backend/` et `frontend/`. Le dossier `tests/` inclus est uniquement celui de Playwright, à la racine, pas `backend/tests/`.

## 1. Démarrage isolé
Ouvrez CMD à la racine du projet :

```cmd
cd /d G:\tests\GaragePro_Complet_Visibilite_Vehicules_CRUD_RDV_Statuts
call DEMARRER_ETAPE4.cmd
curl.exe http://127.0.0.1:18082/api/health
```

Puis ouvrez `http://127.0.0.1:13000` et vérifiez que la page Connexion s'affiche. Cette stack utilise les ports **13000 (frontend)** et **18082 (backend)** et une base nommée **garagepro_e2e**. Elle ne touche pas au projet sur 3000/8000 ou à celui de l'étape 3 sur 18081.

## 2. Installer et lancer Playwright

Prérequis : Docker Desktop actif et Node.js/npm installés.

```cmd
call LANCER_ETAPE4.cmd
```

ou, si les dépendances sont déjà installées :

```cmd
npx playwright test --project=chromium
npx playwright test --project=firefox
```

## 3. Résultats

- `reports/e2e-results.xml` : rapport JUnit exploitable dans le rapport ISO.
- `reports/e2e-html/index.html` : rapport HTML de la campagne.
- `test-results/` : traces/captures des échecs uniquement.
- `npx playwright show-report reports/e2e-html` : ouvrir le rapport.

**Ne déclarez pas les tests PASS avant de les avoir exécutés.** Le pack est une suite préparée. Selon les modifications locales du frontend, les sélecteurs peuvent nécessiter un ajustement, sans changer le métier.

## 4. Huit scénarios E2E

| ID | Scénario | Vérification attendue |
|---|---|---|
| E2E-01 | Accueil de connexion | Formulaire visible |
| E2E-02 | Mot de passe erroné | Message d'erreur |
| E2E-03 | ADMIN | Menu Utilisateurs et Pièces accessible |
| E2E-04 | CLIENT | Pas de création intervention |
| E2E-05 | CLIENT | Formulaire de véhicule visible |
| E2E-06 | CLIENT | Formulaire de rendez-vous visible |
| E2E-07 | MÉCANICIEN | Pages RDV/interventions, création interdite |
| E2E-08 | ADMIN | Déconnexion opérationnelle |

## 5. Nettoyage

```cmd
call ARRETER_ETAPE4.cmd
```

Cela arrête les conteneurs E2E et conserve le volume E2E. **Ne pas utiliser** `docker compose down -v`, `docker volume prune`, ni supprimer les volumes de l'application habituelle.

## 6. Note sur les limitations

Ces 8 scénarios sont de vrais tests UI automatisés, mais ne couvrent pas encore l'enchaînement complet rendez-vous accepté → réparation → facture ni l'accessibilité formelle. Ils constituent le premier lot à élargir après une exécution probante.
