# GaragePro — Gestion de garage automobile

Projet métier **FastAPI + React + PostgreSQL**, préparé selon les exigences fonctionnelles de la **section 4** du cahier des charges du projet ISO/IEC 25010.

> **Livraison demandée : SANS tests.** Ce ZIP ne contient ni suites pytest/Playwright, ni scripts Locust/Bandit/pip-audit/ZAP, ni rapports de tests. Une conformité ISO 25010 ne peut pas être affirmée sans les exécuter et fournir des preuves réelles.

## Démarrage rapide avec Docker (recommandé)

Prérequis : Docker Desktop et Docker Compose.

```bash
cp .env.example .env   # Windows PowerShell : Copy-Item .env.example .env
# Choisir de vraies valeurs pour POSTGRES_PASSWORD et JWT_SECRET dans .env
docker compose up --build -d
```

- **Interface React :** http://localhost:3000
- **Documentation interactive API :** http://localhost:8000/docs
- **Santé API :** http://localhost:8000/api/health

Le serveur initialise les tables au démarrage. Des comptes de démonstration sont créés uniquement si la table utilisateurs est vide et `SEED_DEMO=true`.



**Sécurité :** ces identifiants sont réservés à une machine de développement. Désactiver `SEED_DEMO`, définir des mots de passe secrets forts, un `JWT_SECRET` aléatoire et ajouter une couche HTTPS avant toute publication. Ne pas utiliser la configuration Docker d'exemple directement en production.

## Démarrage local sans Docker

Prérequis : Python 3.11+ et Node.js 20+, npm. Le backend utilise SQLite par défaut pour faciliter la démonstration locale ; PostgreSQL est utilisé via Docker.

Terminal 1 :

```bash
cd backend
python -m venv .venv
# Windows : .venv\Scripts\activate
# Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Terminal 2 :

```bash
cd frontend
npm install
npm run dev
```

Ouvrir http://localhost:5173. La variable `VITE_API_URL` permet de configurer l'adresse de l'API à la compilation du frontend.

## Les trois rôles

- **ADMIN :** tous les véhicules, utilisateurs, mécaniciens, pièces, rendez-vous, interventions, facturation, audit et statistiques.
- **MECANICIEN :** accès en lecture aux ressources autorisées, suivi de ses interventions affectées, changement d'état et consommation de pièces.
- **CLIENT :** auto-inscription, gestion de ses véhicules et rendez-vous, création de demandes de réparation, consultation de ses factures.

## Fonctionnalités principales

1. Authentification JWT et rôles différenciés.
2. Gestion des véhicules, pièces, mécaniciens, rendez-vous et interventions avec opérations CRUD encadrées.
3. Workflow des interventions : `REQUESTED` → `DIAGNOSIS` → `REPAIR` → `COMPLETED` (et annulation avant réparation).
4. Historique d'audit des changements.
5. Consommation de pièces avec verrouillage en base PostgreSQL et contrôle de stock.
6. Factures calculées à partir de la main-d'œuvre et des pièces réellement consommées, avec statut payé/non payé.
7. Tableau de bord agrégé et recherche par immatriculation, description ou référence de pièce.
8. Documentation interactive OpenAPI via FastAPI.

## Parcours de démonstration

1. Se connecter en tant qu'administrateur.
2. Se connecter comme client, enregistrer un véhicule et demander une intervention.
3. Revenir comme administrateur, affecter le mécanicien à l'intervention.
4. Se connecter comme mécanicien, passer en `DIAGNOSIS` puis en `REPAIR` en fournissant un diagnostic.
5. En tant qu'admin, ajouter une pièce en stock si besoin ; revenir mécanicien et consommer une pièce.
6. Terminer l'intervention ; en tant qu'admin, émettre la facture, la marquer comme payée et consulter l'audit.

## Dossiers

```text
GaragePro_ISO25010/
├── backend/
│   ├── app/main.py              # Modèles, routes, JWT, règles métier
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/main.jsx             # Interface responsive et gestion des rôles
│   ├── src/style.css
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── CONCEPTION.md
│   ├── REGLES_METIER.md
│   ├── MATRICE_EXIGENCES.csv
│   └── ISO25010_A_COMPLETER.md
├── docker-compose.yml
└── .env.example
```

## Remarques

- Les transitions de statuts ne sont **pas** un simple CRUD : elles utilisent une route dédiée, avec validation des règles métier.
- L'absence de tests est volontaire et demandée. Le document `docs/ISO25010_A_COMPLETER.md` décrit les preuves manquantes nécessaires au rendu final du cours.
- Les modèles sont créés automatiquement pour le prototype. Pour une exploitation à long terme, ajouter Alembic pour les migrations, HTTPS, rotation des secrets, sauvegardes et supervision.
- Les documents utilisent le modèle **à huit caractéristiques** fourni dans le cahier des charges de cours.


## Correction de connexion (version 1.1)

- Le login envoie exclusivement `email` et `password` à FastAPI, même après une inscription.
- L’inscription d’un nouveau client le connecte automatiquement une fois son compte créé.
- Les comptes de démonstration sont identifiés par `@gmail.com` (ils ne constituent pas de vraies boîtes Gmail).
- Sur une ancienne installation Docker, les comptes déjà présents en PostgreSQL restent inchangés lors d’un rebuild. Si les comptes existants utilisent encore `@example.com` ou `@garagepro.local`, voir `MIGRATION_EMAILS_GMAIL.md`. Un redémarrage Docker ne change pas les emails déjà stockés.

### Mise à jour Docker depuis une ancienne version

Depuis le dossier `GaragePro_ISO25010` :

```cmd
docker compose up -d --build
```

Accéder ensuite à `http://localhost:3000`, actualiser avec `Ctrl+Shift+R`, puis se connecter avec `admin@gmail.com` et le mot de passe défini par `DEMO_PASSWORD` à la création initiale du compte (par défaut `Demo12345!`).

**Ne pas exécuter `docker compose down -v`** : cela supprime le volume contenant les données PostgreSQL.

## Création des utilisateurs dans l’interface

Connectez-vous comme administrateur, puis ouvrez **Utilisateurs** dans la barre latérale.
Cliquez sur **Ajouter**, remplissez **nom complet, email, mot de passe (8 caractères minimum)** et choisissez le rôle **CLIENT**, **MECANICIEN** ou **ADMIN**.
La création passe par `POST /api/users` ; seuls les administrateurs ont accès à cette rubrique.

Pour ajouter un profil mécanicien, créez d'abord un utilisateur avec le rôle **MECANICIEN**, puis ouvrez **Mécaniciens → Ajouter** et choisissez son nom dans la liste déroulante.
Le menu Utilisateurs affiche les comptes mais ne propose pas leur modification ou suppression, car l'API actuelle ne fournit pas ces opérations.

Cette version masque les identifiants de démonstration sur la page de connexion.


## Impression des factures

Depuis la rubrique **Factures**, cliquer sur **Imprimer** pour ouvrir une version A4.
Le bouton **Imprimer / Enregistrer en PDF** utilise la boîte de dialogue du navigateur.
Une intervention terminée doit d'abord être facturée par l'administrateur.
Les détails de la main-d'œuvre et des pièces sont chargés depuis l'API, ainsi que le véhicule et le client.
**Important :** ajouter les coordonnées réelles et les mentions fiscales du garage avant toute remise à un client.
Si une fenêtre ne s'ouvre pas, autoriser les pop-ups pour localhost:3000.


## Rôle MÉCANICIEN — Espace actif

Le compte mécanicien dispose d'un tableau de bord **Mes missions affectées**. Il peut consulter ses rendez-vous, véhicules liés et pièces, ouvrir **Interventions**, passer de Demande → Diagnostic → Réparation → Terminé, renseigner le diagnostic obligatoire, choisir les pièces par nom et quantité, et saisir un **Compte rendu** contenant travaux effectués et observations. L'accès et les modifications sont limités aux interventions qui lui sont réellement affectées.

Un compte rendu est stocké dans une table `work_reports` créée automatiquement au démarrage. La création/modification est réservée au mécanicien affecté et nécessite le statut Diagnostic, Réparation ou Terminé. L'Admin et le client propriétaire peuvent consulter le compte rendu via l'API `GET /api/interventions/{id}/report`.

**Pour tester :** connectez-vous comme Admin, créez une intervention avec un mécanicien sélectionné et enregistrez-la. Connectez-vous ensuite comme ce mécanicien. Le tableau de bord affiche ses missions. Dans Interventions, utilisez **Avancer le travail**, **+ Pièce** et **Compte rendu**. Rechargez pour vérifier les changements.

Les volumes Docker PostgreSQL existants restent conservés si vous reconstruisez sans `down -v`. Aucun test ISO 25010 n'est inclus dans cette livraison.


## Recherche et filtres (version mise à jour)
La recherche dans les rubriques est instantanée et insensible aux accents/majuscules.
Les listes Interventions et Factures proposent un filtre de statut. Rendez-vous,
Interventions, Factures et Audit proposent un filtre par date. Le bouton
« Effacer les filtres » réinitialise tous les critères.
Les filtres sont appliqués côté React aux lignes autorisées par l’API : pour
une très grande base, ajouter ensuite une pagination et un filtrage serveur.


## Validation des rendez-vous par le mécanicien

- Un rendez-vous nouvellement créé commence avec `PENDING` (En attente).
- Dans **Rendez-vous**, le mécanicien affecté voit le bouton **Accepter**.
- `PATCH /api/appointments/{id}/accept` requiert le JWT de ce mécanicien (`MECANICIEN`) ; l'API vérifie l'affectation, le statut et les conflits de planning.
- Après acceptation, le statut devient `PLANNED` (Planifié). L'action est journalisée (`ACCEPT_APPOINTMENT`).
- Un rendez-vous déjà accepté ne peut pas être accepté à nouveau et les clients ne peuvent pas accepter.
- Les anciens rendez-vous `PLANNED` restent planifiés après mise à jour, sans migration destructive.
- Un rendez-vous `PENDING` sans mécanicien attend une affectation par l'administrateur ; la confirmation nécessite un mécanicien affecté.
- Ne supprimez pas votre volume PostgreSQL lors du déploiement.
