from backend.services.profiler import records


def chart_for(df, operation, plan=None):
    if df.empty:
        return None
    sample = df.head(200)
    nums = sample.select_dtypes(include="number").columns.tolist()
    cats = [c for c in sample.columns if c not in nums]
    if not nums:
        return None
    if operation == "correlation":
        values = records(sample[nums])
        return {
            "data": [
                {
                    "type": "heatmap",
                    "x": nums,
                    "y": sample.iloc[:, 0].astype(str).tolist(),
                    "z": [[row[c] for c in nums] for row in values],
                }
            ],
            "layout": {"title": {"text": "상관관계 (Pearson)"}},
        }
    if plan and operation in ["trend", "growth_rate", "moving_average"]:
        time = plan.time_column
        columns = plan.columns
        if operation == "growth_rate":
            columns = [c + "_growth_pct" for c in columns]
        elif operation == "moving_average":
            columns = [c + "_moving_avg" for c in columns]
        data = []
        grouped = (
            sample.groupby(plan.group_by, dropna=False, sort=False)
            if plan.group_by
            else [((), sample)]
        )
        for key, group in grouped:
            label = (
                " / ".join(map(str, key if isinstance(key, tuple) else (key,)))
                if plan.group_by
                else ""
            )
            rows = records(group[[time] + columns])
            for col in columns:
                if len(data) >= 20:
                    break
                data.append(
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": f"{label} · {col}" if label else col,
                        "x": [r[time] for r in rows],
                        "y": [r[col] for r in rows],
                    }
                )
        return {
            "data": data,
            "layout": {
                "title": {"text": "기간별 추세 (최대 200점 / 20개 선)"},
                "xaxis": {"title": {"text": time}},
            },
        }
    if plan and operation == "regression":
        a, b = plan.columns[:2]
        rows = records(sample.sort_values(a))
        return {
            "data": [
                {
                    "type": "scatter",
                    "mode": "markers",
                    "name": "관측값",
                    "x": [r[a] for r in rows],
                    "y": [r[b] for r in rows],
                },
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": "회귀 예측",
                    "x": [r[a] for r in rows],
                    "y": [r["prediction"] for r in rows],
                },
            ],
            "layout": {
                "title": {"text": "단순 선형 회귀"},
                "xaxis": {"title": {"text": a}},
                "yaxis": {"title": {"text": b}},
            },
        }
    keys = plan.group_by if plan and plan.group_by else cats[:2]
    x = (
        sample[keys].astype(str).agg(" · ".join, axis=1).tolist()
        if keys
        else list(range(1, len(sample) + 1))
    )
    if len(set(x)) < len(x):
        x = [f"{label} · #{i + 1}" for i, label in enumerate(x)]
    if operation in {"difference", "ratio"}:
        nums = [operation]
    data = []
    serialized = records(sample[nums])
    for col in nums[:8]:
        data.append(
            {"type": "bar", "name": col, "x": x, "y": [r[col] for r in serialized]}
        )
    return {
        "data": data,
        "layout": {
            "barmode": "group",
            "title": {"text": "분석 결과 (최대 200점)"},
            "xaxis": {"title": {"text": " · ".join(keys) or "행"}},
        },
    }
