@echo off
setlocal
cd /d "%~dp0"

echo Stopping stale API listeners (ports 8000-8005)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backend\scripts\stop_api.ps1"

echo Starting Network Lens backend...
start "Network Lens API" cmd /k "cd /d %~dp0backend && run.bat"

timeout /t 3 /nobreak >nul

echo Starting Network Lens frontend...
start "Network Lens UI" cmd /k "cd /d %~dp0frontend && run.bat"

echo.
echo Network Lens dev environment starting.
echo Backend and frontend open in separate windows.
echo Open http://localhost:5173 when Vite is ready.
