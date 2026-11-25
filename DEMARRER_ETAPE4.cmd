@echo off
setlocal
cd /d "%~dp0"
echo [Etape 4] Demarrage de GaragePro E2E TEST (13000 et 18082)...
docker compose -f docker-compose.e2e.yml -p garagepro_e2e_tests up -d --build --wait
if errorlevel 1 (
  echo ECHEC. Consulter les journaux avec :
  echo docker compose -f docker-compose.e2e.yml -p garagepro_e2e_tests logs --tail=80
  exit /b 1
)
echo TEST FRONTEND : http://127.0.0.1:13000
echo TEST BACKEND : http://127.0.0.1:18082/api/health
