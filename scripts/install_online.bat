@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r backend\requirements.lock.txt
if errorlevel 1 goto fail
cd frontend
call npm ci --no-audit --no-fund
if errorlevel 1 goto fail
call npm run build
if errorlevel 1 goto fail
echo 설치 완료. scripts\start_all.bat를 실행하세요.
pause
exit /b 0
:fail
echo 설치 실패. Python 3.12, Node.js 22 이상과 인터넷 접근을 확인하세요.
pause
exit /b 1
