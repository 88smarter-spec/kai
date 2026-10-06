# V1 검증 기록

검증 환경: Linux, Python 3.12.14, Node.js 24.19.0, 시스템 Chromium. Windows는 이 환경에 설치되어 있지 않음.

## 확인한 기능과 근거

| 항목 | 결과 |
|---|---|
| Backend 테스트 | pytest 26개 통과: API, 파서, 정제, 분석, 보안, localhost LLM 프로토콜 |
| React/TypeScript 배포 빌드 | `tsc -b && vite build` 성공 |
| 실제 브라우저 흐름 | Playwright 4개 통과: 붙여넣기·업로드·페이지 이동·정제·GAP·차트 유형·자동 분석·다중 데이터셋·JOIN·파생 데이터셋·AI 계획 확인/해석 |
| 단일 서버 배포 화면 | FastAPI 정적 빌드 제공 모드에서 브라우저 테스트 통과 |
| 한글 텍스트 | UTF-8-SIG, CP949, EUC-KR 디코딩과 TSV 등록 테스트 통과 |
| 계산 정확성 | 샘플 GAP -20, 사업 A 인력 합계 425, 추세 시간 순서, 증감률·이동평균·회귀·피벗·상관계수 검증 |
| 10만 행 입력 | 4열 TSV 파싱+프로파일 1.584초, 원본+정제 약 37.95MB (현재 테스트 머신의 1회 측정이며 Windows 성능 보장 아님) |
| 10만 행 집계 | DuckDB 결과 A/B 각각 합계 100,000, 일반 결과 500행 제한 검증 |
| JOIN 결과 보존 | 600행 결과를 새 데이터셋에 600행 모두 저장. 미리보기 상한으로 잘리지 않음 |
| 안전한 분석 | 임의 operation/추가 code 필드 거부, 존재하지 않는 컬럼 거부, 숫자 타입 검증, JOIN 폭증 거부 |
| 외부 LLM 주소 | 외부 호스트·속임수 localhost·사용자정보 URL 거부, 프록시 사용/리다이렉트 비활성화 |
| 숫자 근거 검사 | 계산 근거에 없는 999 응답 차단, 계획의 N 옵션을 숫자 근거로 취급하지 않음 |
| 모델 서버 장애 | Python 계산 결과 유지, 기본 분석 독립 동작 |
| 오프라인 설치 자료 | Windows x64 CPython 3.12용 33개 wheel + SHA-256 pinning. `--no-index --require-hashes` 의존성/무결성 dry-run 성공 |
| 외부 프론트엔드 요청 | 브라우저 실행 중 외부 자산 요청 없음. 폰트/Plotly/아이콘 로컬 포함 |

## 검토에서 발견하고 수정한 문제

- 점이 여러 개 있는 버전 문자열/날짜가 숫자로 잘못 변환되던 문제: 정규식 수정과 변환 성공 개수 확인. 원문 손실 회귀 테스트 추가.
- 상수 컬럼의 상관관계 heatmap에 NaN이 남아 API 오류를 내던 문제: null 직렬화. 회귀 테스트 추가.
- 그룹별 추세에서 시간 대신 그룹 이름을 축으로 쓰던 문제: 선택한 시간 기준·그룹별 선 사용. 숫자 기간과 그룹 추세 테스트 추가.
- 잘못된 열 수가 있는 데이터에서 헤더 자동 감지가 앞의 행을 건너뛰던 문제: 선택한 헤더 폭을 기준으로 검사하고 오류 반환.
- 표 헤더 접근성: 명시적 column scope 추가.
- 자동 Swagger UI의 CDN 의존: 비활성화하고 로컬 OpenAPI JSON만 제공.
- 검증 중 Vite가 dist를 재생성하는 순간 Backend를 시작한 초기 실행은 개발 안내 화면을 반환해 브라우저 테스트가 실패했음. 빌드 완료 후 Backend 재시작으로 해결하고 최종 배포 흐름 재검증. 설치/실행 BAT는 빌드와 실행을 분리함.

독립 코드 검토 후 위의 3개 주요 문제를 수정했고 해당 범위 재검토에서 추가 주요 문제 없음.

## 아직 검증하지 않은 항목

- **실제 Qwen3-14B 모델 추론과 llama.cpp CUDA 서버**: 현재 머신에 llama-server, GGUF, NVIDIA 도구가 없음. HTTP 모의 서버로 `/models`, JSON 계획, Python 실행, 한국어 응답 표시만 검증함. 실제 모델의 JSON 형식 준수·해석 품질·지연 시간은 미검증.
- **Windows BAT 실제 실행**: Windows cmd/Python Launcher 환경이 없어 실행하지 못함. Windows 전용 wheel은 다운로드와 해시/의존성 해석만 검증했고 설치/런타임 실행을 주장하지 않음.
- **회사 DRM Excel의 실제 Ctrl+C**: 실제 파일과 Windows Excel이 없음. 표준 text/plain TAB clipboard paste 이벤트와 원본 범위 예제로 검증함. 회사 DRM 정책이 복사를 허용해야 함.
- 실제 Quadro RTX 4000 8GB에서 `-ngl 20 -c 8192`의 적합성: 예시값이며 대상 PC에서 조정 필요.

따라서 소프트웨어와 오프라인 배포 자료는 준비되어 있으나, 사용자가 정의한 V1 완료 기준 중 실제 Qwen/Windows/회사 Excel 확인은 대상 PC에서 남아 있습니다.

## 알려진 경고

pytest에는 Starlette TestClient와 최신 AnyIO 간 deprecated alias 경고 1개가 있음. 테스트 실패/런타임 앱 오류는 아님. Playwright 실행 환경의 FORCE_COLOR/NO_COLOR 경고도 기능 실패는 아님.

## 대상 PC 최종 확인 순서

1. Python 3.12 x64 설치 → install_offline.bat → start_all.bat.
2. 실제 Excel 범위 복사·붙여넣기, CP949 TSV 업로드, 기본 GAP/추세/차트 확인.
3. llama.cpp CUDA 배포와 Qwen GGUF 경로 설정 → start_llm_example.bat.
4. LLM 설정 연결 확인 → 자연어 질문 → JSON 계획 확인 → 계산 결과/한국어 해석 확인.
5. GPU 메모리/지연 시간에 맞춰 GPU offload와 context 조정. 보고서 숫자를 Python 근거와 대조.
