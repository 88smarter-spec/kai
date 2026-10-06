@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist "wheelhouse" (
  echo wheelhouse가 없습니다. 인터넷 연결 Windows PC에서 prepare_offline.bat를 실행하여 반입하세요.
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  echo frontend\dist가 없습니다. 인터넷 연결 PC에서 빌드한 dist 폴더를 반입하세요.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --no-index --find-links wheelhouse --require-hashes -r backend\requirements.offline.txt
if errorlevel 1 goto fail
echo 오프라인 설치 완료. start_all.bat를 실행하세요. 배포 모드에서는 Node.js가 필요하지 않습니다.
pause
exit /b 0
:fail
echo 오프라인 설치 실패. Python 3.12 64-bit와 wheelhouse 파일을 확인하세요.
pause
exit /b 1
