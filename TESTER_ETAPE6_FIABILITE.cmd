@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "PROJECT=garagepro_e2e_tests"
set "COMPOSE=docker-compose.e2e.yml"
set "BASE=docker compose -f %COMPOSE% -p %PROJECT%"
if not exist "%COMPOSE%" (
  echo ERREUR : %COMPOSE% introuvable. Placez ce script a la racine GaragePro.
  exit /b 1
)
if not exist "reports\reliability" mkdir "reports\reliability"
set "LOG=reports\reliability\etape6_resultats.txt"
>"%LOG%" echo GaragePro - Etape 6 - Fiabilite - %DATE% %TIME%
echo [REL-01] Controle du serveur E2E...
curl.exe -fsS --max-time 10 http://127.0.0.1:18082/api/health >nul
if errorlevel 1 goto :failure
echo [REL-01] OK>>"%LOG%"
echo [REL-04] Comptage des enregistrements avant restart DB...
call :count users BEFORE_USERS
if errorlevel 1 goto :failure
call :count vehicles BEFORE_VEHICLES
if errorlevel 1 goto :failure
echo AVANT users=!BEFORE_USERS!, vehicles=!BEFORE_VEHICLES!>>"%LOG%"
echo [REL-04] Redemarrage PostgreSQL E2E...
%BASE% restart db_e2e
if errorlevel 1 goto :failure
set "DB_OK=0"
for /l %%I in (1,1,30) do (
  if "!DB_OK!"=="0" (
    %BASE% exec -T db_e2e pg_isready -U garagepro_e2e -d garagepro_e2e >nul 2>&1
    if not errorlevel 1 (set "DB_OK=1") else (timeout /t 2 /nobreak >nul)
  )
)
if "!DB_OK!"=="0" goto :failure
call :count users AFTER_USERS
if errorlevel 1 goto :failure
call :count vehicles AFTER_VEHICLES
if errorlevel 1 goto :failure
echo APRES users=!AFTER_USERS!, vehicles=!AFTER_VEHICLES!>>"%LOG%"
if not "!BEFORE_USERS!"=="!AFTER_USERS!" goto :failure
if not "!BEFORE_VEHICLES!"=="!AFTER_VEHICLES!" goto :failure
echo [REL-04] OK : nombres users et vehicles inchanges.
echo [REL-04] OK>>"%LOG%"
echo [REL-05] Verification apres 3 redemarrages backend...
for /l %%R in (1,1,3) do (
  %BASE% restart backend_e2e
  if errorlevel 1 goto :failure
  set "READY=0"
  for /l %%I in (1,1,30) do (
    if "!READY!"=="0" (
      curl.exe -fsS --max-time 5 http://127.0.0.1:18082/api/health >nul 2>&1
      if not errorlevel 1 (set "READY=1") else (timeout /t 2 /nobreak >nul)
    )
  )
  if "!READY!"=="0" goto :failure
  echo [REL-05] Cycle %%R OK
  echo [REL-05] Cycle %%R OK>>"%LOG%"
)
echo [ETAPE 6] TOUS LES CONTROLES AUTOMATISES ONT REUSSI.
echo SUCCES>>"%LOG%"
echo Journal : %LOG%
exit /b 0
:count
set "VALUE="
for /f "usebackq delims=" %%V in (`%BASE% exec -T db_e2e psql -U garagepro_e2e -d garagepro_e2e -At -c "SELECT COUNT(*) FROM %~1;" 2^>nul`) do set "VALUE=%%V"
if not defined VALUE exit /b 1
set "%~2=!VALUE!"
exit /b 0
:failure
echo [ETAPE 6] ECHEC : voir la commande precedente.
echo ECHEC>>"%LOG%"
echo Journal : %LOG%
exit /b 1
