@echo off
cd /d "%~dp0\backend"

echo === Unit tests ===
call .venv\Scripts\python.exe -m pytest -q
if errorlevel 1 exit /b 1

echo.
echo === In-process smoke ===
call .venv\Scripts\python.exe scripts\smoke_test.py
if errorlevel 1 exit /b 1

if exist .api_port (
  set /p API_PORT=<.api_port
  echo.
  echo === Live smoke on port %API_PORT% ===
  call .venv\Scripts\python.exe scripts\smoke_test.py --live http://127.0.0.1:%API_PORT%
  if errorlevel 1 exit /b 1
) else (
  echo.
  echo Skipping live smoke — no backend\.api_port ^(start backend with run.bat first^)
)

echo.
echo All validation passed.
