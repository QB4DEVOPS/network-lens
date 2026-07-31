@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)

for /f %%p in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure_port.ps1"') do set PORT=%%p

echo.
echo Running smoke tests (in-process)...
.venv\Scripts\python.exe scripts\smoke_test.py
if errorlevel 1 (
  echo Smoke tests failed — fix before starting the API.
  exit /b 1
)

echo.
echo Starting API on http://127.0.0.1:%PORT%
echo Frontend .env synced — restart frontend if it is already running.
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port %PORT%
