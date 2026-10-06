# Excel Data 분석 시스템

**Windows 설치 패키지:** [kai-windows-offline.zip 다운로드](https://github.com/88smarter-spec/kai/raw/refs/heads/main/releases/kai-windows-offline.zip) (약 93MB). Python 3.12 x64 설치 후 압축을 풀고 `scripts\install_offline.bat`, `scripts\start_all.bat` 순서로 실행하세요.

Windows 10/11 망분리 PC에서 실행하는 로컬 분석 웹앱입니다. Excel에서 범위를 복사해 붙여넣거나 TXT/TSV/CSV 텍스트를 등록합니다. **XLS/XLSX 파일을 읽지 않습니다. DRM이 허용하는 복사 기능으로 추출한 텍스트만 사용합니다.**

Python이 숫자를 계산하고 로컬 Qwen이 결과를 해석합니다. 인터넷 API, CDN, 외부 폰트, 원격 저장, 사용량 수집을 사용하지 않습니다. 실행 시 서버는 `127.0.0.1`에만 바인딩합니다.

## 가장 쉬운 실행 — Windows 오프라인 배포

제공된 `kai-windows-offline.zip`에는 앱 소스, 빌드된 화면, **Windows x64 / Python 3.12용 wheelhouse**가 들어 있습니다. 별도 Python 설치 파일과 LLM 파일은 포함하지 않습니다.

1. Windows에 **Python 3.12 64-bit**를 설치합니다. 설치 화면에서 Python Launcher와 PATH 추가를 선택합니다.
2. ZIP을 `C:\ExcelAnalysis`처럼 쓰기 가능한 폴더에 압축 해제합니다.
3. `scripts\install_offline.bat`를 더블클릭합니다. 네트워크 없이 wheelhouse에서 해시를 검증하며 패키지를 설치합니다.
4. `scripts\start_all.bat`를 더블클릭합니다. Backend 창이 열리고 준비되면 기본 브라우저가 `http://127.0.0.1:8000`을 엽니다. 기본 브라우저를 Chrome으로 지정하면 Chrome으로 열립니다.
5. **데이터 추가 → Excel 붙여넣기**로 시작합니다. AI를 사용하려면 아래의 llama.cpp 서버도 별도 실행합니다.

빌드된 배포 모드는 **Node.js가 필요하지 않습니다**. Backend 콘솔 창을 닫으면 서버가 종료되고 메모리 데이터도 사라집니다. 데이터/채팅은 앱 재시작 시 복구되지 않습니다. 원본 업무 데이터를 자동 저장하지 않습니다.

이 저장소의 `frontend/dist`와 `wheelhouse`는 생성물로 Git에서 제외됩니다. ZIP에는 포함합니다. Git 소스만 복사한 경우 아래의 연결 가능한 PC 준비 단계가 필요합니다.

## 기능

- Excel `Ctrl+C → Ctrl+V`, UTF-8 / UTF-8-SIG / CP949 / EUC-KR TXT·TSV와 CSV 입력
- 이름 변경·삭제가 가능한 다중 데이터셋, 서버 페이지네이션(50행), 원본/정제 결과 비교
- 헤더 자동 감지, 시작 행 지정(1-based), 1~3행 헤더 결합, 중복 이름 처리
- 공백·결측·빈 행/열·합계 후보 정제, 천 단위 숫자·날짜·% 변환과 경고
- 컬럼 프로파일: 타입, 결측, 고유값, 최소/최대, 평균, 중앙값, 표준편차, 상위 값
- 기초 통계 / 그룹 집계 / 전체 집계 / 피벗 / 필터 / 정렬 / 상위·하위 N / 차이 / 비율 / 증감률 / 이동평균 / 상관관계 / IQR·Z-score 이상치 / 추세 / JOIN / 결측 / 중복 / 단순 회귀
- Plotly의 line, grouped bar, stacked bar, scatter, histogram, box, heatmap. 로컬 JS에 포함되어 인터넷이 필요 없음
- 전체 자동 분석, 구조 기반 추천 분석, 계산 근거와 JSON 계획 표시
- JSON 분석 계획 → 사용자 확인 → allowlist 도구 → Python 계산 → 한국어 LLM 해석
- localhost LLM 설정·연결 확인, 경영진 보고서, 결과 JSON/해석 TXT 내려받기
- JOIN/분석 결과 전체를 새 메모리 데이터셋으로 등록하여 후속 분석
- 10만 행 이상은 DuckDB로 그룹 집계. 미리보기 50행, 결과 전송 500행, 차트 200점 제한

## 폴더 구조

```text
kai/
  backend/
    main.py                  FastAPI, localhost 보호, 정적 화면 제공
    models.py                검증된 분석 계획·입력 모델
    api/                     dataset / analysis / chat API
    services/
      clipboard_parser.py    CSV quoting 지원 TSV 파서·인코딩
      data_cleaner.py         원본 보존 정제
      dataframe_service.py   메모리 데이터셋
      profiler.py            통계 프로파일
      analysis_engine.py     안전한 계산 도구
      automatic_analysis.py  자동·추천 분석
      chart_engine.py        차트 데이터
      query_planner.py       자연어 → 검증된 JSON
      llm_client.py          localhost 전용 LLM
    tests/                   API·계산·보안·LLM 프로토콜 테스트
    requirements.txt         주요 런타임 의존성
    requirements.lock.txt    전이 의존성 포함 정확한 버전
    requirements.offline.txt Windows wheel SHA-256 목록
  frontend/
    src/components/          입력·표·차트·분석·채팅·설정
    src/services/            상대경로 API 호출
    src/types/               타입
    src/App.tsx              3영역 워크스페이스
    tests/                   Chromium 실제 UI 흐름
    dist/                    빌드된 배포 화면 (생성물)
  scripts/                   설치·실행 BAT와 배포 유틸리티
  samples/                   가상 인력·생산 TSV
  wheelhouse/                Windows 오프라인 Python 패키지 (생성물)
  docs/                      구현 계획·검증 보고서
```

## 개발용 설치 — 인터넷 연결 PC

Python 3.12 64-bit, Node.js 22 이상, Chrome을 설치합니다. Windows에서는 `scripts\install_online.bat`가 아래 작업을 수행합니다.

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
cd frontend
npm ci --no-audit --no-fund
npm run build
```

실행만 하는 대상 PC에는 Node가 없어도 됩니다. 화면 소스를 수정/빌드하려면 Node가 필요합니다. `npm ci`는 저장소의 `package-lock.json`을 그대로 사용합니다.

개발 시 창을 두 개 열어 실행합니다.

```bat
scripts\start_backend.bat
scripts\start_frontend.bat
```

개발 화면: `http://127.0.0.1:5173`, Backend: `http://127.0.0.1:8000`, API 스키마: `http://127.0.0.1:8000/api/openapi.json` (인터넷 자산을 사용하는 Swagger UI는 비활성화).

Linux에서 검증/개발할 때:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock.txt
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# 별도 터미널에서 개발 화면 실행
npm --prefix frontend run dev
```

`dist`가 이미 있으면 `start_all.bat`는 배포 모드를 선택합니다. 개발 서버를 사용하려면 `start_backend.bat`와 `start_frontend.bat`를 직접 실행합니다. 빌드한 뒤 Backend를 재시작해야 정적 화면이 마운트됩니다.

## 오프라인 반입 준비

인터넷 연결 **Windows x64, Python 3.12** PC에서 `install_online.bat` 실행 후 `prepare_offline.bat`를 실행합니다. wheelhouse 다운로드, SHA-256 목록 생성, 프론트엔드 빌드를 수행합니다. 준비 단계만 인터넷이 필요합니다.

반입 목록:

- 이 프로젝트 전체와 `frontend/dist`, `wheelhouse`, `backend/requirements.offline.txt`
- Python 3.12 x64 공식 설치 파일
- Chrome 설치 파일(대상 PC에 없다면)
- **선택:** Node.js 설치 파일, 동일 Windows에서 준비한 `frontend/node_modules` (오프라인 개발/재빌드용)
- **AI 사용 시:** llama.cpp Windows CUDA 배포 ZIP의 전체 파일, Qwen GGUF 모델 파일
- GPU 드라이버와 배포본이 요구하는 Microsoft Visual C++ Redistributable 설치 파일

`.venv`는 경로/OS에 종속되어 PC 간 복사하지 않습니다. 대상에서 `install_offline.bat`로 새로 만듭니다. wheelhouse의 패키지 버전이나 Python 버전을 임의 변경하면 해시/휠 호환성 검증이 실패합니다. 버전 변경은 연결 PC에서 다시 준비하세요. npm 개발 설치가 필요한 경우 `node_modules`도 준비해야 하며, 실행 전용 배포에는 필요하지 않습니다.

## llama.cpp와 Qwen 연결

1. 연결 가능한 PC에서 공식 `ggml-org/llama.cpp` 릴리스의 **Windows CUDA 빌드**와 신뢰할 수 있는 Qwen3-14B Q4_K_M GGUF를 확보합니다. 다운로드 출처와 제공되는 체크섬을 확인하고 승인된 절차로 반입합니다.
2. `scripts\start_llm_example.bat`의 `LLAMA_SERVER`, `GGUF_MODEL`을 실제 경로로 변경합니다. llama-server 옆 DLL도 함께 보관해야 합니다.
3. BAT를 실행합니다. 예시 명령:

```bat
llama-server.exe -m "C:\local-ai\models\Qwen3-14B-Q4_K_M.gguf" --host 127.0.0.1 --port 8080 -c 8192 -ngl 20 --parallel 1 --alias qwen-local
```

4. 앱의 **LLM 설정**에서 API URL `http://127.0.0.1:8080/v1`, Model 빈칸(자동 감지), Temperature `0.2`, Max Tokens `2048`로 **연결 확인** 후 저장합니다.
5. 데이터셋을 선택하고 AI 질문을 보냅니다. JSON 계획과 JOIN 키를 확인한 다음 **계획 확인 후 실행**을 누릅니다.

Quadro RTX 4000 8GB에서 14B Q4 전체 GPU 적재는 어려울 수 있습니다. 위 값은 **미검증 시작 예시**이며 최적값이 아닙니다. VRAM 부족 시 `-ngl`과 컨텍스트를 낮춥니다. CPU/RAM offload 때문에 속도가 느릴 수 있고 실제 GPU 드라이버·llama.cpp 빌드에 따라 지원 여부가 다릅니다. 컨텍스트가 너무 작으면 질문을 단순화하고 데이터셋/컬럼 수를 줄이세요. 서버 로그를 보며 조정하세요.

앱은 `/v1/models`, `/v1/chat/completions`를 사용하고 Qwen의 thinking 비활성화 옵션을 전달합니다. JSON response_format을 지원하는 최근 llama.cpp 서버가 필요합니다. 런타임에 모델을 다운로드하지 않습니다.

실제 모델 연결이 없어도 Preview, 정제, 프로파일, 모든 기본 도구와 차트는 동작합니다. 자연어 계획 생성은 로컬 모델이 필요합니다. 해석 중 연결이 끊기면 Python 결과를 유지하고 연결 오류를 알립니다.

## 데이터 입력과 분석

**Excel:** 필요한 범위에 헤더를 포함해 선택 → Ctrl+C → 데이터 추가 → 입력 영역 Ctrl+V → 이름과 헤더 설정 → 데이터 등록. 회사 DRM 정책에서 복사를 허용해야 합니다. 앱은 DRM을 우회하지 않습니다.

**TXT/TSV:** 데이터 추가 → 텍스트 파일 → `.txt`/`.tsv` 선택. TAB 구분이 기본입니다. `.csv`는 쉼표 구분입니다. 한국어 인코딩은 자동 시도합니다. 따옴표로 묶은 줄바꿈/탭 필드도 지원합니다. Excel 파일 직접 업로드는 거부합니다.

**헤더:** 시작 행은 복사한 텍스트 기준 1부터 셉니다. 제목 행은 자동으로 건너뛰는 휴리스틱을 사용하지만 복잡한 병합 헤더는 시작 행을 직접 지정하세요. 2~3행 결합은 같은 열의 텍스트를 ` / `로 연결합니다. 병합 셀의 빈 영역을 임의 채우지는 않습니다. 잘못 인식한 헤더는 데이터셋을 삭제하고 올바른 설정으로 다시 등록하세요.

**정제:** 숫자 변환은 비결측 값 전체가 숫자인 경우 적용합니다. 숫자와 문자가 섞였으면 문자를 유지하고 경고합니다. `0012` 같은 식별자는 문자로 유지합니다. `15%`는 `0.15`로 변환하고, 샘플의 `잔업률=15`는 % 기호가 없으므로 그대로 `15`입니다. 날짜는 명확한 연-월-일 패턴에만 적용합니다. 원본/정제 결과 버튼으로 비교할 수 있습니다.

**GAP:** 기본 분석 → 차이/GAP → 첫 컬럼 가용인력, 두 번째 소요인력 → 실행. `가용 − 소요`이므로 음수는 부족입니다. 샘플 첫 행은 `210 − 230 = -20`입니다. 비율은 첫 컬럼÷둘째 컬럼이며 %가 아닙니다.

**JOIN과 후속 효율 분석:** 데이터셋 2개 등록 → JOIN 도구에서 두 번째 데이터셋과 `사업, 월` 입력 → 실행 → JOIN 키/중복 키 경고 확인 → **결과를 데이터셋으로** 등록 → 새 데이터셋에서 공수÷생산량 비율을 계산합니다. 데이터셋 등록은 화면에 표시한 500행만이 아니라 **전체 계산 결과**를 보관합니다. 다대다 결합은 행·합계를 늘릴 수 있습니다. 결측 키끼리도 매칭되므로 먼저 검토하세요. 자연어 복합 분석도 V1에서는 한 단계씩 계획을 확인하며 수행합니다.

**추세/증감률:** 월·기간의 숫자 순서를 인식합니다. 증감률/이동평균은 기간순 행 기준이므로 같은 기간의 여러 행은 먼저 범주/기간별로 집계하세요. 월별 자료가 여러 연도에 걸치면 연도를 포함한 날짜/기간 컬럼이 필요합니다.

**통계 해석:** 상관관계는 인과관계가 아닙니다. 이상치는 오류 확정이 아닌 검토 후보입니다. 숫자형이라는 이유만으로 인력·비율·기간값의 합계가 업무적으로 유효한 것은 아니므로 평균 등 적절한 집계 함수를 선택하세요.

## 보안·데이터 보관

- Backend에서 `exec`, `eval`, 셸 명령, 모델 생성 SQL을 실행하지 않습니다. Pydantic이 operation, 집계 함수, 컬럼, 필터와 JOIN을 검증합니다.
- LLM 주소는 `127.0.0.1`, `localhost`, `::1`의 HTTP `/v1`만 허용합니다. localhost를 직접 loopback으로 정규화하며 프록시/DNS·리다이렉트를 통해 외부에 보내지 않습니다.
- LLM 계획에는 데이터셋 이름/ID·행수·컬럼 타입/결측 메타데이터를 전달합니다. 해석에는 제한된 계산 결과만 전달합니다. 전체 DataFrame을 보내지 않습니다.
- AI 답변의 수치가 근거에 없으면 응답을 차단합니다. 이 검사는 보수적인 수치 존재 검사로, 값의 업무 의미나 AI의 모든 추론을 보증하지 않습니다. 표시한 Python 계산 근거와 함께 검토하세요.
- 업무 데이터와 채팅을 자동 파일 저장하지 않습니다. 파일 업로드 처리에는 프레임워크의 임시 파일이 사용될 수 있으며 요청 처리 후 닫습니다. 결과 저장 버튼을 누를 때만 사용자가 선택한 다운로드 폴더에 결과가 저장됩니다.
- 앱은 단일 사용자 로컬 도구입니다. 인증·공유 서버용 접근제어는 제공하지 않습니다. `--host 0.0.0.0` 등으로 외부에 공개하지 마세요.
- 데이터셋 20개/합산 DataFrame 약 1.5GB, 입력 50MB/50만 행/200열, JOIN 예상 100만 행을 제한합니다. 동시 입력 파싱 중 메모리는 추가 사용될 수 있습니다.

## 테스트

```sh
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run build
# Backend 8000 / Vite 5173를 켠 뒤
CHROMIUM_PATH=/usr/bin/chromium npm --prefix frontend test
```

Windows 브라우저 테스트는 연결 PC에서 `cd frontend`, `npx playwright install chromium`, `npm test`로 실행합니다. 오프라인 검증하려면 Playwright 브라우저 바이너리도 별도로 준비해야 합니다. `CHROMIUM_PATH`로 설치된 Chromium 실행 파일을 지정할 수 있습니다. `APP_URL`로 빌드된 앱 주소를 지정할 수 있습니다.

현재 검증 결과와 미검증 항목은 `docs/VALIDATION.md`를 확인하세요. 모의 localhost LLM 테스트는 프로토콜 검증이며 실제 Qwen 추론 검증을 대체하지 않습니다.

## 오류 해결

| 상황 | 확인할 항목 |
|---|---|
| TAB 구분이 감지되지 않음 | 두 개 이상의 열을 포함한 Excel 범위를 복사. 쉼표 데이터는 CSV 선택 |
| 행의 열 수가 헤더와 다름 | 복사 범위/따옴표/헤더 시작 행 확인. 잘못된 행을 조용히 버리지 않음 |
| 한글 인코딩 실패 | 파일을 UTF-8 또는 CP949 텍스트로 저장. XLS/XLSX를 확장자만 바꾸면 안 됨 |
| 숫자 컬럼이 분석에 안 잡힘 | 프로파일과 정제 경고 확인. 단위 문자/혼합 텍스트를 정리하고 재등록 |
| JOIN KEY 없음 / 타입 불일치 | 양쪽 컬럼명과 정제 타입 일치, 키 구분은 쉼표 |
| 포트 사용 중 | 기존 Backend/Vite/llama-server 창 확인, 중복 실행한 창 종료 |
| 로컬 AI 연결 실패 | llama-server 실행, GGUF 경로, `8080/v1`, `/models` 응답 확인 |
| AI 계획 검증 실패 | 실제 컬럼명으로 질문 단순화. 기본 분석 도구는 계속 사용 가능 |
| 근거 없는 수치 응답 차단 | 숫자를 만들어낸 응답은 표시하지 않음. Python 결과를 확인하고 재질문 |
| 서버 재시작 후 데이터 없음 | RAM 저장 방식의 정상 동작. 원본 Excel 범위를 다시 붙여넣기 |
| Python 또는 py 명령 없음 | Python 3.12 x64 재설치 시 Launcher/PATH 선택 |
| 오프라인 휠/해시 실패 | ZIP/반입 파일 무결성, Python 3.12 x64, wheelhouse와 해시 파일 일치 확인 |

## 현재 한계와 이후 개선

- 실제 Windows 10/11 + Quadro RTX 4000 + Qwen3-14B 검증은 대상 하드웨어에서 필요합니다.
- 복합 자연어 질문을 여러 도구로 자동 연쇄 실행하는 기능은 제공하지 않습니다. 결과 데이터셋을 등록해 단계별로 진행합니다.
- 추천/자동 분석은 규칙 기반입니다. 의미를 고려한 AI 추천·업종별 보고서 템플릿은 추가 개선 대상입니다.
- 복잡한 병합 헤더의 가로 채우기, 이상치 수정, 데이터 영구 저장, 사용자 인증, 통계 유의성 검정은 V1 범위 밖입니다.
- 같은 숫자가 다른 의미로 잘못 쓰인 LLM 응답은 수치 존재 검사만으로 잡을 수 없습니다. 향후 인용 ID와 문장별 근거 검증을 강화할 수 있습니다.
- 차트·표 반환 상한은 명시적으로 표시합니다. 전체 분석 결과를 보존하려면 결과를 데이터셋으로 등록하세요.
