# GaragePro — Véhicules / rendez-vous / statuts

## Règles

- ADMIN : visualise tous les véhicules, peut en ajouter pour un client, gérer les rendez-vous.
- MÉCANICIEN : voit **tous les véhicules créés par l’ADMIN** (détectés via le journal d’audit `CREATE` sur `vehicles`), ainsi que les véhicules des clients **après acceptation** de leurs rendez-vous (statut `PLANNED`). Il conserve aussi l'accès à ses interventions affectées. Consultation des photos incluse, sans permission d'écriture.
- CLIENT : voit uniquement ses véhicules et ses rendez-vous; peut créer, consulter, modifier un rendez-vous `PENDING`, supprimer un rendez-vous `PENDING` ou `REJECTED` non lié à une intervention. Un rendez-vous confirmé `PLANNED` est verrouillé pour empêcher les modifications de planning sans validation.
- MÉCANICIEN : seul celui affecté peut cliquer « Accepter », uniquement si le rendez-vous est `PENDING` et sans conflit de planning. Le serveur passe le statut à `PLANNED`.
- CLIENT : voit « En attente » puis « Planifié » dans son onglet Rendez-vous (rafraîchissement automatique toutes les 12 secondes; bouton Actualiser disponible).

## Important concernant les anciens véhicules

La détection des voitures créées par l'ADMIN est basée sur les entrées d'audit déjà présentes : `audit_logs.action=CREATE`, `resource=vehicles` et créateur avec rôle `ADMIN`. Un véhicule historique sans journal d'audit n'est pas automatiquement considéré comme créé par l'ADMIN : il faut vérifier sa provenance; ce choix évite d'exposer arbitrairement les véhicules privés d'autres clients.

## Installation en conservant la base existante

1. Sauvegardez le volume PostgreSQL ou faites un `pg_dump`.
2. Remplacez les fichiers du projet existant par ceux du ZIP (ou seulement `backend/app/main.py` et `frontend/src/main.jsx`).
3. **Ne faites jamais** `docker compose down -v`, `docker volume prune`, `docker volume rm`.
4. Depuis le dossier **existant**, lancez `docker compose up -d --build backend frontend`.
5. Accédez à http://localhost:3000 ; Ctrl+Shift+R.
6. Vérifiez les utilisateurs `@gmail.com`; les comptes existants ne sont pas recréés lors d'un rebuild.

## Parcours de vérification

1. ADMIN crée un véhicule pour un CLIENT; MÉCANICIEN peut consulter le véhicule et sa photo.
2. CLIENT crée un véhicule puis un rendez-vous affecté au mécanicien : statut En attente; MÉCANICIEN ne voit pas encore ce véhicule (sauf s'il est associé à une intervention existante).
3. CLIENT peut modifier et supprimer ses demandes En attente; il ne peut pas modifier celles d'autrui.
4. CLIENT crée un autre RDV; MÉCANICIEN clique Accepter; statut Planifié.
5. CLIENT voit automatiquement Planifié; MÉCANICIEN voit désormais ce véhicule et sa photo.
6. L'édition/suppression par le CLIENT d'un rendez-vous Planifié retourne HTTP 409.
