# V1 구현 계획

목표: Windows 망분리 PC에서 Excel 복사 텍스트를 분석하는 localhost 웹앱.

1. FastAPI, 메모리 DatasetStore, TSV/CSV 인코딩·헤더 파서, 정제와 프로파일을 구현한다. 실제 데이터·오류·숫자 정확성을 pytest로 검증한다.
2. Pydantic allowlist 분석 계획으로 18개 도구와 JOIN·회귀를 구현한다. exec/eval/SQL 문자열 실행은 사용하지 않는다. 결과는 제한된 행과 차트로 반환한다.
3. React/TypeScript/Vite/Tailwind/Plotly UI: 여러 데이터셋, 입력·정제·미리보기·도구·차트·채팅·설정을 연결한다. 브라우저 테스트로 붙여넣기와 분석을 검증한다.
4. localhost만 허용하는 llama.cpp 클라이언트: 계획→검증→Python 계산→한국어 해석. 모델 없으면 기본 도구 유지. 모의 localhost 서버로 프로토콜과 실패 경로를 검증하고 실제 모델 검증 여부를 명시한다.
5. Windows BAT, wheelhouse 오프라인 설치와 정적 빌드 단일 서버 실행, README와 sample TSV를 제공한다. API 통합 테스트·빌드·브라우저·10만 행 검증 후 완료 범위를 기록한다.

데이터는 RAM에만 보관하고 원본 파일은 읽지 않는다. LLM 출력은 명령이 아닌 데이터로 취급한다. JOIN 키와 결과의 누락·샘플링을 UI에 표시한다. 런타임 외부 요청·CDN·텔레메트리 없음.
