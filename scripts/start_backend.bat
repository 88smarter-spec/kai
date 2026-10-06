@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Python 가상환경이 없습니다. scripts\install_online.bat 또는 install_offline.bat를 먼저 실행하세요.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 pause
