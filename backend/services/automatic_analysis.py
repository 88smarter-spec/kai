from backend.models import AnalysisPlan
from backend.services.analysis_engine import execute_plan


def recommendations(dataset, others):
    p = dataset.profiling
    nums = p["numeric_columns"]
    cats = p["categorical_columns"]
    times = p["date_columns"]
    if not times:
        times = [
            c
            for c in dataset.frame.columns
            if any(
                x in c.lower() for x in ["월", "년", "일자", "분기", "date", "month"]
            )
        ]
    entries = []

    def add(title, operation, **args):
        entries.append(
            {
                "title": title,
                "plan": AnalysisPlan(
                    dataset=dataset.id, operation=operation, **args
                ).model_dump(),
            }
        )

    add("데이터 품질과 기초 통계", "describe")
    add("결측값 현황", "missing")
    add("중복 행 확인", "duplicates")
    if nums:
        add("숫자 컬럼 종합 집계", "aggregate", metrics={c: "sum" for c in nums[:8]})
        if cats:
            add(
                f"{cats[0]}별 숫자 비교",
                "groupby",
                group_by=[cats[0]],
                metrics={c: "sum" for c in nums[:8]},
            )
        if times:
            add(
                f"{times[0]} 기준 추세", "trend", time_column=times[0], columns=nums[:5]
            )
            add(
                "기간별 증감률",
                "growth_rate",
                time_column=times[0],
                columns=nums[:3],
                group_by=[c for c in cats[:1] if c != times[0]],
            )
        if len(dataset.frame) >= 4:
            add("IQR 이상치 후보", "outliers", columns=nums[:8])
    if len(nums) >= 2 and len(dataset.frame) >= 3:
        add("숫자 컬럼 상관관계", "correlation", columns=nums[:8])
    available = next((c for c in nums if "가용" in c), None)
    required = next((c for c in nums if "소요" in c), None)
    if available and required:
        add("가용인력 − 소요인력 GAP", "difference", columns=[available, required])
    for other in others:
        if other.id == dataset.id:
            continue
        common = [
            c
            for c in dataset.frame.columns
            if c in other.frame.columns and c not in nums
        ][:5]
        if common:
            add(
                f"{other.name} 결합 후보 · 키: " + ", ".join(common),
                "join",
                other_dataset=other.id,
                join_keys=common,
            )
    return entries


def automatic(dataset, frames):
    analyses = []
    skipped = []
    plans = recommendations(dataset, [])[:10]
    for item in plans:
        if item["plan"]["operation"] == "join":
            continue
        try:
            analyses.append(
                {
                    "title": item["title"],
                    "result": execute_plan(
                        AnalysisPlan.model_validate(item["plan"]), frames
                    ),
                }
            )
        except ValueError as exc:
            skipped.append({"title": item["title"], "reason": str(exc)})
    summary = [
        f"{dataset.name}: {len(dataset.frame):,}행, {len(dataset.frame.columns)}열.",
        f"결측 셀 {dataset.profiling['null_count']:,}개, 중복 추가 행 {dataset.profiling['duplicates']:,}개.",
    ]
    for analysis in analyses:
        result = analysis["result"]
        if result["operation"] == "outliers":
            summary.append(
                f"IQR 기준 이상치 후보 {result['total_rows']:,}행. 오류 여부는 추가 확인이 필요합니다."
            )
    return {
        "summary": summary,
        "analyses": analyses,
        "skipped": skipped,
        "recommendations": plans,
        "notes": [
            "정량 요약은 Python 계산 결과입니다. 원인 판단은 추가 데이터 확인이 필요합니다.",
            "비율·인력·기간 등 모든 숫자 컬럼의 합계가 업무적으로 유효한 것은 아닙니다. 집계 함수를 검토하세요.",
        ],
    }
