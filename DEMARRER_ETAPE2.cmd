@echo off
setlocal
cd /d "%~dp0"
echo === ETAPE 2 GARAGEPRO : PostgreSQL de test ISOLE ===
echo Le service de production GaragePro reste INCHANGE.
docker compose -f docker-compose.integration.yml -p garagepro_integration_tests up -d --wait
if errorlevel 1 (
    echo ERREUR : PostgreSQL de test n'a pas demarre.
    exit /b 1
)
py -3.12 -m pip install -r backend\requirements.txt -r backend\requirements-integration.txt
if errorlevel 1 (
    echo ERREUR : installation des dependances.
    exit /b 1
)
if not exist "%TEMP%\garagepro-reports" mkdir "%TEMP%\garagepro-reports"
echo === EXECUTION DES TESTS D'INTEGRATION POSTGRESQL ===
py -3.12 -m pytest backend\integration_pg -v -p no:cacheprovider --junitxml="%TEMP%\garagepro-reports\integration-postgresql.xml"
if errorlevel 1 (
    echo ECHEC OU ERREUR : lire les details ci-dessus.
    exit /b 1
)
echo.
echo SUCCES - preuve XML: %TEMP%\garagepro-reports\integration-postgresql.xml
endlocal
