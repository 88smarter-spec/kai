import logging
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.api import dataset, analysis, chat

logger = logging.getLogger("kai")
app = FastAPI(
    title="Excel Data 분석 시스템",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


def is_local(address):
    try:
        return urlsplit(address).hostname in {"127.0.0.1", "localhost", "::1"}
    except ValueError:
        return False


@app.middleware("http")
async def local_only(request: Request, call_next):
    host = request.headers.get("host", "")
    origin = request.headers.get("origin")
    if not is_local("http://" + host) or origin and not is_local(origin):
        return JSONResponse({"detail": "localhost 접근만 허용합니다."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' http://127.0.0.1:8000 ws://127.0.0.1:5173 ws://localhost:5173; worker-src 'self' blob:; object-src 'none'; frame-ancestors 'none'"
    )
    return response


@app.exception_handler(ValueError)
async def value_error(request: Request, exc: ValueError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("API operation failed: %s", request.url.path)
    return JSONResponse(
        {
            "detail": "처리 중 오류가 발생했습니다. 입력 형식과 데이터 타입을 확인해주세요. 개발자 로그에 상세 오류가 기록되었습니다."
        },
        status_code=500,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "storage": "memory", "network": "localhost only"}


app.include_router(dataset.router)
app.include_router(analysis.router)
app.include_router(chat.router)

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/favicon.svg")
    def favicon():
        return FileResponse(DIST / "favicon.svg")

    @app.get("/")
    def index():
        return FileResponse(DIST / "index.html")
else:

    @app.get("/")
    def index():
        return {
            "message": "개발 모드: frontend에서 npm run dev를 실행하세요. 배포 모드: npm run build 후 Backend를 재시작하세요."
        }
