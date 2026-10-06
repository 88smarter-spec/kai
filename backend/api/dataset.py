import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Query
from pydantic import BaseModel, Field
from backend.models import PasteRequest, CleanOptions
from backend.services.clipboard_parser import parse_text, decode_file
from backend.services.data_cleaner import clean_frame
from backend.services.dataframe_service import store
from backend.services.profiler import records, profile
from backend.services.automatic_analysis import recommendations, automatic

router = APIRouter(prefix="/api/datasets")


def metadata(d):
    return {
        "id": d.id,
        "name": d.name,
        "row_count": len(d.frame),
        "column_count": len(d.frame.columns),
        "cleaning": d.cleaning,
    }


@router.get("")
def list_datasets():
    with store.lock:
        return [metadata(d) for d in store.items.values()]


@router.post("/paste")
def paste(body: PasteRequest):
    raw, frame, info = parse_text(
        body.text, body.header_start, body.header_rows, body.delimiter, body.options
    )
    return metadata(store.add(body.name, raw, frame, info))


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    name: str = Form(""),
    header_start: int | None = Form(None),
    header_rows: int = Form(1),
    options: str = Form("{}"),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in [".txt", ".tsv", ".csv"]:
        raise ValueError(
            "TXT/TSV/CSV 텍스트만 지원합니다. Excel 파일은 직접 읽지 않습니다."
        )
    content = await file.read(50_000_001)
    await file.close()
    if len(content) > 50_000_000:
        raise ValueError("입력 파일은 최대 50MB입니다.")
    try:
        opts = CleanOptions.model_validate(json.loads(options))
    except Exception as exc:
        raise ValueError("정제 옵션이 올바르지 않습니다.") from exc
    if (
        not 1 <= header_rows <= 3
        or header_start is not None
        and not 1 <= header_start <= 100
    ):
        raise ValueError("헤더 시작 행은 1~100, 헤더 개수는 1~3이어야 합니다.")
    text, encoding = decode_file(content)
    raw, frame, info = parse_text(
        text, header_start, header_rows, "comma" if extension == ".csv" else "tab", opts
    )
    info["encoding"] = encoding
    return metadata(
        store.add(name.strip()[:100] or Path(file.filename).stem, raw, frame, info)
    )


@router.get("/{identifier}")
def get_dataset(
    identifier: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    source: str = Query("clean", pattern="^(clean|raw)$"),
):
    d = store.get(identifier)
    frame = d.raw if source == "raw" else d.frame
    return {
        **metadata(d),
        "preview": records(frame.iloc[offset : offset + limit]),
        "columns": frame.columns.tolist(),
        "preview_total": len(frame),
        "profile": d.profiling,
        "recommendations": recommendations(d, list(store.items.values())),
    }


class Rename(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.patch("/{identifier}")
def rename(identifier: str, body: Rename):
    if not body.name.strip():
        raise ValueError("데이터셋 이름을 입력해주세요.")
    with store.lock:
        d = store.get(identifier)
        d.name = body.name.strip()
        return metadata(d)


@router.delete("/{identifier}")
def delete(identifier: str):
    with store.lock:
        store.get(identifier)
        del store.items[identifier]
    return {"deleted": True}


@router.post("/{identifier}/clean")
def clean(identifier: str, body: CleanOptions):
    with store.lock:
        d = store.get(identifier)
        frame, info = clean_frame(d.raw, body)
        if frame.empty:
            raise ValueError("정제 후 데이터가 없습니다.")
        d.frame = frame
        d.cleaning = {**d.cleaning, **info}
        d.profiling = profile(frame)
        return metadata(d)


@router.post("/{identifier}/auto")
def auto(identifier: str):
    return automatic(store.get(identifier), store.frames())
