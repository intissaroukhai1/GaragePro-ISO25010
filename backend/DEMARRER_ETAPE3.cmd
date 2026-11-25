@echo off
setlocal
cd /d "%~dp0"
echo [Etape 3] Demarrage de la stack API TEST uniquement (port 18081)...
docker compose -f docker-compose.api-tests.yml -p garagepro_api_tests up -d --build --wait
if errorlevel 1 (
  echo ECHEC de demarrage. Consultez les logs :
  echo docker compose -f docker-compose.api-tests.yml -p garagepro_api_tests logs backend_api_tests
  exit /b 1
)
echo.
echo Verification du serveur de test :
curl.exe -f http://127.0.0.1:18081/api/health
if errorlevel 1 (
  echo Le backend est peut-etre encore en demarrage. Consultez les logs.
  exit /b 1
)
echo.
echo Serveur de test : http://127.0.0.1:18081/docs
