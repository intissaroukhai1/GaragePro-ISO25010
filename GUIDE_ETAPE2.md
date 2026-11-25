# GaragePro — Etape 2 : tests d'integration PostgreSQL

## Objectif (cahier des charges, section 7)
Verifier les interactions **API FastAPI ↔ PostgreSQL**, la persistance, les relations entre entites, les droits d'acces, les transactions, le stock et la facturation. Outil : pytest + FastAPI TestClient + PostgreSQL 16. **Aucun resultat n'est declare avant execution sur votre PC.**

## SECURITE DES DONNEES
- Ce kit ne remplace **aucun** fichier existant `main.py`, `main.jsx` ou les tests de l'etape 1.
- La BDD de test s'appelle `garagepro_integration_test` avec l'utilisateur `garagepro_test`.
- Elle ecoute sur `127.0.0.1:55432`, pas sur le port 5432 de production. Aucun volume `garagepro_db` n'est utilise.
- Le conteneur de test utilise `tmpfs` : aucune persistance de la BDD lorsque le conteneur s'arrete. Elle est **volontairement vide au prochain demarrage**.
- Les tables de cette BDD de test sont recreees avant chaque test. Une garde de securite verifie le nom de BDD, l'utilisateur et le port **avant** de faire le moindre `drop_all`.
- **N'executer que** `backend/integration_pg`. Ne pas lancer `pytest backend/tests backend/integration_pg` en une seule commande : les deux suites chargent le meme module app.main avec des connexions differentes.
- Ne jamais utiliser `docker compose down -v` sur le projet GaragePro.

## Installer les nouveaux fichiers
Decompresser le ZIP, copier son contenu dans le dossier principal existant :

`G:\tests\GaragePro_Complet_Visibilite_Vehicules_CRUD_RDV_Statuts\`

Vous aurez notamment :

```text
GaragePro_Complet_Visibilite_Vehicules_CRUD_RDV_Statuts/
  docker-compose.yml                   [deja present, INCHANGE]
  docker-compose.integration.yml       [nouveau]
  backend/
    app/main.py                        [deja present, INCHANGE]
    requirements.txt                   [deja present, INCHANGE]
    requirements-integration.txt       [nouveau]
    integration_pg/
      conftest.py                       [nouveau]
      test_integration_postgresql.py    [nouveau]
  DEMARRER_ETAPE2.cmd                  [nouveau]
  ARRETER_BD_TEST.cmd                  [nouveau]
  GUIDE_ETAPE2.md                      [nouveau]
```

**Ne pas** remplacer `backend/tests/conftest.py` : notre fichier est dans `backend/integration_pg/conftest.py`.

## Option rapide : en un clic
Double-cliquer sur `DEMARRER_ETAPE2.cmd` ou l'executer depuis CMD. Lancer **seulement** après avoir verifie que Docker Desktop fonctionne.

## Option manuelle : etape par etape (CMD Windows)

1. Aller au projet :

```cmd
cd /d G:\tests\GaragePro_Complet_Visibilite_Vehicules_CRUD_RDV_Statuts
```

2. Demarrer **uniquement** la base de test :

```cmd
docker compose -f docker-compose.integration.yml -p garagepro_integration_tests up -d --wait
```

3. Verifier qu'elle est `healthy` :

```cmd
docker compose -f docker-compose.integration.yml -p garagepro_integration_tests ps
```

4. Installer les dependances si necessaire :

```cmd
py -3.12 -m pip install -r backend\requirements.txt -r backend\requirements-integration.txt
```

5. Executer les **8 tests d'integration** (seulement ce dossier) :

```cmd
py -3.12 -m pytest backend\integration_pg -v -p no:cacheprovider
```

6. Generer un rapport XML :

```cmd
if not exist "%TEMP%\garagepro-reports" mkdir "%TEMP%\garagepro-reports"
py -3.12 -m pytest backend\integration_pg -v -p no:cacheprovider --junitxml="%TEMP%\garagepro-reports\integration-postgresql.xml"
```

7. A la fin, arreter la base **de test** :

```cmd
docker compose -f docker-compose.integration.yml -p garagepro_integration_tests down
```

**Ne pas utiliser** la commande generale `docker compose down` pour l'application principale.

## Liste des tests

| ID | Test | Preuve attendue |
|----|------|-----------------|
| PG-01 | Connexion reellement PostgreSQL 16 | Nom/driver de BDD et version serveur |
| PG-02 | CRUD vehicules ADMIN + audit | `INSERT`, `UPDATE`, `DELETE` persistes |
| PG-03 | CRUD rendez-vous CLIENT | `PENDING`, modification, suppression persistees |
| PG-04 | Acceptation par mecanicien | `PLANNED` en PostgreSQL et visibilite du vehicule CLIENT |
| PG-05 | Controle d'acces + conflit horaire | Refus HTTP 403 / 409, statut inchange |
| PG-06 | Intervention et rapport | Creation ADMIN, transitions et rapport persistes |
| PG-07 | Consommation de plusieurs pieces | Stock diminue, alertes et aucune demi-transaction |
| PG-08 | Facture et paiement | Montant calcule, facture visible, paiement et audit |

## Resultat et evaluation

Attendu si la version du backend correspond a celle analysee : `8 passed`.
Il faut d'abord executer les commandes sur votre ordinateur : **aucun PASS n'est encore revendique pour PostgreSQL ici**.

Les tests PostgreSQL completeront les 16 tests unitaires/API SQLite reussis a l'etape 1 et permettront de justifier l'**aptitude fonctionnelle** et une partie de la **fiabilite** demandee par ISO/IEC 25010.

Si `port is already allocated 55432`, un autre service utilise le port de test. N'arretez pas votre BDD GaragePro de production : envoyez les logs pour choisir un port de test libre.

Si `connection refused`, verifier Docker Desktop et `ps`, puis `docker compose -f docker-compose.integration.yml -p garagepro_integration_tests logs dbtest`.

La version de projet peut differer de celle analysee. Ne pas modifier les assertions pour masquer une anomalie ; identifier les regles et corriger le vrai probleme si necessaire.
