from pydantic import BaseModel, Field
from backend.services.analysis_engine import compute_frame
from backend.api.dataset import metadata
from fastapi import APIRouter
from backend.models import AnalysisPlan
from backend.services.analysis_engine import execute_plan
from backend.services.dataframe_service import store

router = APIRouter()


@router.post("/api/analysis")
def analyze(body: AnalysisPlan):
    return execute_plan(body, store.frames())


class SaveAnalysis(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    plan: AnalysisPlan


@router.post("/api/analysis/save")
def save_analysis(body: SaveAnalysis):
    frame, warnings, details = compute_frame(body.plan, store.frames())
    if frame.empty:
        raise ValueError("빈 분석 결과는 데이터셋으로 등록할 수 없습니다.")
    return metadata(
        store.add(
            body.name,
            frame.astype("string"),
            frame.copy(),
            {
                "removed_rows": 0,
                "removed_columns": 0,
                "total_candidates": 0,
                "warnings": warnings,
                "derived_plan": body.plan.model_dump(),
            },
        )
    )
