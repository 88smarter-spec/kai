@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.12 scripts\prepare_ai_bundle.py --zip
if errorlevel 1 (
  echo 준비에 실패했습니다. 위 오류와 Python 3.12 설치를 확인하세요.
)
pause
