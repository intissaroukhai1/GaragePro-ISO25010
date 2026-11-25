@echo off
setlocal
cd /d "%~dp0"
echo [Etape 5] Installation isolee de Locust dans .venv-locust...
py -3.12 -m venv .venv-locust
if errorlevel 1 goto :fail
"%~dp0.venv-locust\Scripts\python.exe" -m pip install "locust>=2.40,<3"
if errorlevel 1 goto :fail
echo.
echo Installation OK. Prochaine commande : TESTER_ETAPE5.cmd
exit /b 0
:fail
echo Echec installation. Envoyez les dernieres lignes de CMD.
exit /b 1
