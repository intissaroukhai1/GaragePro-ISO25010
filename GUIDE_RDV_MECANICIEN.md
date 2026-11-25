# Acceptation des rendez-vous — GaragePro

1. Avec un compte **ADMIN** ou **CLIENT**, créez un rendez-vous et affectez un mécanicien. Son statut initial sera `PENDING` (En attente).
2. Déconnectez-vous. Connectez-vous avec le compte du mécanicien affecté.
3. Dans **Rendez-vous**, la ligne du rendez-vous en attente présente **Accepter**.
4. Cliquez sur **Accepter**. Le statut devient `PLANNED` (Planifié).
5. Le client peut consulter son rendez-vous confirmé. L'ADMIN retrouve l'action dans **Journal d'audit**.

## Règles
- Seul un mécanicien avec le profil affecté peut accepter.
- Un rendez-vous ne peut être accepté qu'une fois.
- Un conflit avec un autre rendez-vous `PLANNED` du même mécanicien renvoie HTTP 409.
- Les données et rendez-vous `PLANNED` préexistants sont préservés.
- Il faut avoir affecté un mécanicien avant son acceptation.

## Installation sur le projet EXISTANT
Remplacer **backend/app/main.py** et **frontend/src/main.jsx** par les fichiers de cette version, après sauvegarde.
Exécuter à la racine : `docker compose up -d --build backend frontend`.
Vider le cache navigateur par Ctrl + Shift + R.
**Ne pas utiliser `docker compose down -v`** et ne pas supprimer les volumes PostgreSQL.
