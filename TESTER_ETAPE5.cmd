@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-locust\Scripts\python.exe" (
  echo Locust non installe. Lancez d'abord INSTALLER_ETAPE5.cmd
  exit /b 1
)
if not exist "tests\performance\locustfile.py" (
  echo Fichier tests\performance\locustfile.py introuvable.
  exit /b 1
)
echo [Etape 5] Verification stricte du serveur E2E local (port 18082)...
"%~dp0.venv-locust\Scripts\python.exe" -c "import json,urllib.request; u='http://127.0.0.1:18082/api/health'; d=json.load(urllib.request.urlopen(u,timeout=5)); assert d.get('service')=='garagepro' and d.get('status')=='ok',d; print('Serveur E2E GaragePro OK')"
if errorlevel 1 (
  echo Le serveur E2E n'est pas pret. Demarrez DEMARRER_ETAPE4.cmd et verifiez le port 18082.
  exit /b 1
)
if not exist "reports\performance" mkdir "reports\performance"
echo [Etape 5] Test initial : 2 utilisateurs, 30 secondes, uniquement GET /api/health.
"%~dp0.venv-locust\Scripts\python.exe" -m locust -f "tests\performance\locustfile.py" --headless --host "http://127.0.0.1:18082" --users 2 --spawn-rate 1 --run-time 30s --csv "reports\performance\garagepro_smoke" --html "reports\performance\garagepro_smoke.html" --exit-code-on-error 1
set RC=%ERRORLEVEL%
echo.
echo Rapport : reports\performance\garagepro_smoke.html
echo Fichiers CSV : reports\performance\garagepro_smoke_*.csv
echo Code de sortie : %RC%
exit /b %RC%
