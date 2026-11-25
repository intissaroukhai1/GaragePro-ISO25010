# Comptes GaragePro en @gmail.com

Comptes de démonstration à la création d’une base **vide** :

| Rôle | Identifiant | Mot de passe initial |
|---|---|---|
| ADMIN | admin@gmail.com | Demo12345! |
| MECANICIEN | mecanicien@gmail.com | Demo12345! |
| CLIENT | client@gmail.com | Demo12345! |

Ces adresses servent d’identifiants de test : elles ne créent pas de véritables boîtes Gmail. Le mot de passe réel d'une base déjà initialisée peut être différent.

## Base PostgreSQL existante

**IMPORTANT :** `docker compose up -d --build` ne modifie jamais automatiquement les emails préexistants. Pour inspecter les comptes :

```cmd
docker compose exec db psql -U garagepro -d garagepro -c "SELECT id,email,role FROM users ORDER BY id;"
```

Avant une modification, sauvegarder la base avec la commande suivante depuis CMD :

```cmd
docker compose exec -T db pg_dump -U garagepro -d garagepro > garagepro_backup.sql
```

Après vérification des comptes et de l’absence de conflit d’adresse, migrer uniquement les trois comptes démo :

```cmd
docker compose exec db psql -U garagepro -d garagepro -c "UPDATE users SET email = CASE email WHEN 'admin@example.com' THEN 'admin@gmail.com' WHEN 'mecanicien@example.com' THEN 'mecanicien@gmail.com' WHEN 'client@example.com' THEN 'client@gmail.com' WHEN 'admin@garagepro.local' THEN 'admin@gmail.com' WHEN 'mecanicien@garagepro.local' THEN 'mecanicien@gmail.com' WHEN 'client@garagepro.local' THEN 'client@gmail.com' ELSE email END WHERE email IN ('admin@example.com','mecanicien@example.com','client@example.com','admin@garagepro.local','mecanicien@garagepro.local','client@garagepro.local');"
```

S'il existe déjà un autre utilisateur avec un de ces emails `@gmail.com`, PostgreSQL refusera la modification pour éviter un doublon : dans ce cas, ne pas écraser le compte existant.

Vérifier :

```cmd
docker compose exec db psql -U garagepro -d garagepro -c "SELECT id,email,role FROM users ORDER BY id;"
```

Les données des véhicules, rendez-vous, interventions et factures ne sont pas affectées par la migration des emails. **Ne pas lancer `docker compose down -v`.** Utiliser le même dossier/projet Docker Compose que celui qui possède votre volume de données.
