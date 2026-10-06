@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo 먼저 인터넷 연결 Windows PC에서 install_online.bat를 실행하세요.
  pause
  exit /b 1
)
if not exist "wheelhouse" mkdir wheelhouse
".venv\Scripts\python.exe" -m pip download --only-binary=:all: -r backend\requirements.lock.txt -d wheelhouse
if errorlevel 1 goto fail
".venv\Scripts\python.exe" scripts\build_offline_requirements.py
if errorlevel 1 goto fail
cd frontend
call npm ci --no-audit --no-fund
if errorlevel 1 goto fail
call npm run build
if errorlevel 1 goto fail
echo 준비 완료. 프로젝트, wheelhouse, frontend\dist와 Python 설치 파일을 반입하세요.
echo .venv는 PC 간 복사하지 마세요. 대상 PC에서 install_offline.bat로 새로 생성합니다.
pause
exit /b 0
:fail
echo 오프라인 준비 실패. 인터넷 연결과 동일한 Windows/Python/아키텍처를 확인하세요.
pause
exit /b 1
