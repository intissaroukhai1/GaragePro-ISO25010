@echo off
cd /d "%~dp0"
docker compose -f docker-compose.e2e.yml -p garagepro_e2e_tests down
echo E2E arretee. Les autres projets et volumes GaragePro sont intacts.
