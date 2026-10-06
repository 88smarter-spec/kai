@echo off
chcp 65001 >nul
rem 반입한 llama.cpp Windows CUDA 배포와 GGUF 경로를 수정하세요.
set "LLAMA_SERVER=C:\local-ai\llama.cpp\llama-server.exe"
set "GGUF_MODEL=C:\local-ai\models\Qwen3-14B-Q4_K_M.gguf"
if not exist "%LLAMA_SERVER%" (
  echo llama-server.exe 경로를 수정하세요: %LLAMA_SERVER%
  pause
  exit /b 1
)
if not exist "%GGUF_MODEL%" (
  echo GGUF 모델 경로를 수정하세요: %GGUF_MODEL%
  pause
  exit /b 1
)
rem 14B Q4는 8GB VRAM에 전체 적재가 어려워 GPU 일부 offload로 시작합니다.
"%LLAMA_SERVER%" -m "%GGUF_MODEL%" --host 127.0.0.1 --port 8080 -c 8192 -ngl 20 --parallel 1 --alias qwen-local
pause
