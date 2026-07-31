@echo off
cd /d "%~dp0"
if not exist "node_modules" (
  echo Installing npm dependencies...
  call npm.cmd install
)
echo Starting UI on http://localhost:5173
call npm.cmd run dev
