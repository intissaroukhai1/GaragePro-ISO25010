@echo off
setlocal
cd /d "%~dp0"
echo [Etape 4] Tests Playwright - Chrome et Firefox
call npm install
if errorlevel 1 exit /b 1
call npx playwright install chromium firefox
if errorlevel 1 exit /b 1
call npx playwright test
exit /b %errorlevel%
