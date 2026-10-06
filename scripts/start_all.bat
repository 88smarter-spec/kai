@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo 먼저 scripts\install_offline.bat 또는 scripts\install_online.bat를 실행하세요.
  pause
  exit /b 1
)
if exist "local-ai\ai-ready.json" start "Local Qwen AI" "%ComSpec%" /k call "%~dp0start_llm.bat"
if exist "frontend\dist\index.html" (
  start "Excel Data Backend" "%ComSpec%" /k call "%~dp0start_backend.bat"
  ".venv\Scripts\python.exe" scripts\wait_ready.py http://127.0.0.1:8000/api/health http://127.0.0.1:8000
  if errorlevel 1 pause
  exit /b
)
if not exist "frontend\node_modules\vite\bin\vite.js" (
  echo frontend\dist 또는 개발용 node_modules가 없습니다. 설치 스크립트를 먼저 실행하세요.
  pause
  exit /b 1
)
start "Excel Data Backend" "%ComSpec%" /k call "%~dp0start_backend.bat"
start "Excel Data Frontend" "%ComSpec%" /k call "%~dp0start_frontend.bat"
".venv\Scripts\python.exe" scripts\wait_ready.py http://127.0.0.1:8000/api/health http://127.0.0.1:5173
if errorlevel 1 pause
