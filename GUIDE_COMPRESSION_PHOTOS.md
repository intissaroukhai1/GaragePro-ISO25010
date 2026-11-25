# GaragePro — compression automatique des photos véhicules

La page Véhicules accepte JPG/PNG/WEBP et compresse dans le navigateur avant envoi (JPEG, max 3 000 000 octets). Les fichiers originaux sont limités à 25 Mo et 35 mégapixels. L’API accepte les photos directes jusqu’à 12 Mo, redimensionne et stocke en JPEG sous 3 Mo. Les données existantes et les comptes @gmail.com restent inchangés.

## Installation Windows

1. Faire une sauvegarde de la base PostgreSQL existante et vérifier le volume monté.
2. Remplacer `frontend/src/main.jsx` et `backend/app/main.py` depuis le ZIP.
3. À la racine du projet actuel : `docker compose up -d --build backend frontend`
4. Actualiser `http://localhost:3000` avec Ctrl+Shift+R.

Ne pas exécuter `docker compose down -v` ni `docker volume prune`.
