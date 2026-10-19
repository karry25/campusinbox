@echo off
cd /d "%~dp0"
py --version >nul 2>&1
if errorlevel 1 (
  python app.py
) else (
  py app.py
)
pause
