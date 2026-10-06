@echo off
chcp 65001 >nul
cd /d "%~dp0..\frontend"
if not exist "node_modules\vite\bin\vite.js" (
  echo 개발용 Node 의존성이 없습니다. 단일 서버 모드는 start_all.bat로 실행하세요.
  pause
  exit /b 1
)
call npm run dev
if errorlevel 1 pause
