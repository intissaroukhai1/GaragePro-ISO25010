@echo off
setlocal
cd /d "%~dp0"
echo Arret de la stack API TEST (AUCUN volume de production)...
docker compose -f docker-compose.api-tests.yml -p garagepro_api_tests down
