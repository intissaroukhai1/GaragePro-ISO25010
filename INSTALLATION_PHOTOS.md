# GaragePro — Photos du garage et des véhicules

## Modifications
- Image originale de garage affichée sur la page de connexion (frontend/public/garage-login.jpg).
- Sélection d’une photo (JPG, PNG, WEBP) lors de la création/modification d’un véhicule.
- Prévisualisation et suppression de la photo depuis le formulaire de modification.
- Colonne Photo dans Véhicules.
- Stockage dans la nouvelle table PostgreSQL `vehicle_photos`, créée automatiquement au démarrage : aucune suppression/modification des tables existantes.
- Lecture et modification des photos protégées par JWT et permissions.

## Installer en conservant vos données
1. Sauvegarder le dossier du projet et, si possible, la base PostgreSQL.
2. Copier `frontend/src/main.jsx`, `frontend/src/style.css`, `frontend/public/garage-login.jpg`, `backend/app/main.py`, `backend/requirements.txt` aux mêmes emplacements dans votre projet existant.
3. Depuis le dossier du projet déjà utilisé, lancer `docker compose up -d --build`.
4. Dans le navigateur, recharger avec Ctrl+Shift+R.
5. Aller à Véhicules -> Ajouter (ou Modifier) -> Photo du véhicule.

Ne jamais exécuter `docker compose down -v`. Si vous démarrez le ZIP dans un nouveau dossier, Docker Compose pourrait utiliser un **nouveau volume**, et vos anciennes données n’apparaîtront pas. Pour conserver les données, appliquer les changements dans **votre dossier de projet existant**.

Aucun dossier de tests ISO 25010 n’est inclus. Vérifier le lancement dans votre environnement Docker.
