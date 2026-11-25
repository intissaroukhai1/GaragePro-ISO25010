@echo off
cd /d "%~dp0"
echo Demarrage de GaragePro (PostgreSQL + FastAPI + React)...
docker compose up -d --build
if errorlevel 1 (
  echo Erreur Docker. Verifiez que Docker Desktop est lance.
  pause
  exit /b 1
)
echo.
echo GaragePro: http://localhost:3000
echo FastAPI Swagger: http://localhost:8000/docs
echo Admin: admin@gmail.com
echo Mot de passe demo: Demo12345! ^(si DEMO_PASSWORD non modifie^)
pause
