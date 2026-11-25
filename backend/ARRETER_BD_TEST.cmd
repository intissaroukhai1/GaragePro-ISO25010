@echo off
cd /d "%~dp0"
echo Arret UNIQUEMENT de la base PostgreSQL de test.
docker compose -f docker-compose.integration.yml -p garagepro_integration_tests down
