import numpy as np
import pandas as pd
import duckdb
from scipy import stats
from sklearn.linear_model import LinearRegression
from backend.models import AnalysisPlan
from backend.services.profiler import profile, records
from backend.services.chart_engine import chart_for


def require_columns(df, columns):
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError("컬럼을 찾을 수 없습니다: " + ", ".join(missing))


def require_numbers(df, columns, minimum=1):
    require_columns(df, columns)
    if len(columns) < minimum:
        raise ValueError(f"숫자형 컬럼을 {minimum}개 이상 선택해주세요.")
    invalid = [c for c in columns if not pd.api.types.is_numeric_dtype(df[c])]
    if invalid:
        raise ValueError("숫자형 컬럼이 필요합니다: " + ", ".join(invalid))


def chronological(df, column, groups):
    require_columns(df, [column] + groups)
    values = df[column]
    if pd.api.types.is_numeric_dtype(values) or pd.api.types.is_datetime64_any_dtype(
        values
    ):
        return df.sort_values(groups + [column], kind="stable")
    # Natural numeric order handles Korean month/quarter labels (1월..12월).
    keys = values.astype(str).str.findall(r"\d+")
    sort_key = (
        keys.map(lambda parts: tuple(map(int, parts)))
        if keys.map(bool).all()
        else values.astype(str)
    )
    return (
        df.assign(__time_sort=sort_key)
        .sort_values(groups + ["__time_sort"], kind="stable")
        .drop(columns="__time_sort")
    )


def apply_filters(df, rules):
    for rule in rules:
        require_columns(df, [rule.column])
        col, value = df[rule.column], rule.value
        try:
            if rule.operator == "contains":
                mask = col.astype("string").str.contains(
                    str(value), regex=False, na=False
                )
            elif rule.operator == "in":
                if not isinstance(value, list) or len(value) > 1000:
                    raise ValueError("in 필터 값은 1000개 이하 목록이어야 합니다.")
                mask = col.isin(value)
            elif rule.operator == "is_null":
                mask = col.isna()
            else:
                mask = {
                    "eq": col.eq,
                    "ne": col.ne,
                    "gt": col.gt,
                    "ge": col.ge,
                    "lt": col.lt,
                    "le": col.le,
                }[rule.operator](value)
            df = df.loc[mask.fillna(False)]
        except (TypeError, KeyError) as exc:
            raise ValueError("필터 값과 컬럼 타입이 맞지 않습니다.") from exc
    return df


def grouped(df, groups, metrics):
    if not metrics:
        raise ValueError("집계할 숫자 컬럼과 함수를 선택해주세요.")
    require_columns(df, groups + list(metrics))
    if len(set(groups)) != len(groups) or set(groups) & set(metrics):
        raise ValueError("그룹 기준과 집계 컬럼은 서로 다른 컬럼이어야 합니다.")
    for col, fn in metrics.items():
        if fn != "count":
            require_numbers(df, [col])
    if len(df) >= 100_000:
        # Relation API with quoted identifiers; no model-provided SQL.
        def quote(col):
            return '"' + col.replace('"', '""') + '"'

        fnmap = {"mean": "avg", "std": "stddev_samp"}
        expressions = [quote(c) for c in groups] + [
            f"{fnmap.get(fn, fn)}({quote(c)}) AS {quote(c)}"
            for c, fn in metrics.items()
        ]
        with duckdb.connect(":memory:") as con:
            result = (
                con.from_df(df)
                .aggregate(",".join(expressions), ",".join(quote(c) for c in groups))
                .df()
            )
        return result.sort_values(groups, kind="stable") if groups else result
    if groups:
        return (
            df.groupby(groups, dropna=False, observed=True, sort=True)
            .agg(metrics)
            .reset_index()
        )
    return pd.DataFrame([{c: getattr(df[c], fn)() for c, fn in metrics.items()}])


def compute_frame(plan: AnalysisPlan, frames: dict[str, pd.DataFrame]):
    if plan.dataset not in frames:
        raise ValueError("분석 대상 데이터셋이 없습니다.")
    df = apply_filters(frames[plan.dataset], plan.filters)
    if df.empty:
        raise ValueError("필터 후 데이터가 없습니다. 조건을 확인해주세요.")
    op = plan.operation
    require_columns(df, plan.columns + plan.group_by)
    warnings, details = [], {}
    if op == "describe":
        details = profile(df)
        out = pd.DataFrame(details["columns"])
        # keep nested summaries out of analysis tables
        out = out.drop(columns=["top_values"])
    elif op in ["groupby", "aggregate"]:
        out = grouped(df, plan.group_by if op == "groupby" else [], plan.metrics)
    elif op == "pivot":
        if not plan.pivot_column or not plan.group_by or len(plan.metrics) != 1:
            raise ValueError("Pivot은 행 키, 열 키, 집계 컬럼 1개가 필요합니다.")
        require_columns(df, [plan.pivot_column])
        if plan.pivot_column in plan.group_by:
            raise ValueError("Pivot의 행 기준과 열 기준은 서로 달라야 합니다.")
        col, fn = next(iter(plan.metrics.items()))
        require_numbers(df, [col])
        if df[plan.pivot_column].nunique() > 100:
            raise ValueError("Pivot 열이 100개를 넘습니다. 먼저 필터링해주세요.")
        out = df.pivot_table(
            index=plan.group_by,
            columns=plan.pivot_column,
            values=col,
            aggfunc=fn,
            observed=True,
        ).reset_index()
        out.columns = out.columns.map(str)
    elif op == "filter":
        out = df[plan.columns] if plan.columns else df
    elif op in ["sort", "top_n", "bottom_n"]:
        if not plan.columns:
            raise ValueError("정렬 기준 컬럼을 선택해주세요.")
        out = df.sort_values(
            plan.columns,
            ascending=(op == "bottom_n") if op != "sort" else plan.ascending,
            kind="stable",
        )
        if op != "sort":
            out = out.head(plan.n)
    elif op in ["difference", "ratio"]:
        require_numbers(df, plan.columns, 2)
        a, b = plan.columns[:2]
        out = df.copy()
        out[op] = (
            df[a] - df[b] if op == "difference" else df[a].div(df[b].replace(0, np.nan))
        )
        details = {
            "formula": f"{a} {'-' if op == 'difference' else '/'} {b}",
            "summary": profile(out[[op]]),
        }
        if op == "ratio" and (df[b] == 0).any():
            warnings.append("분모가 0인 비율은 결측값으로 표시했습니다.")
    elif op in ["trend", "growth_rate", "moving_average"]:
        require_numbers(df, plan.columns)
        if not plan.time_column:
            raise ValueError("시간 기준 컬럼이 필요합니다.")
        if plan.time_column in plan.group_by:
            raise ValueError("시간 기준과 그룹 기준은 서로 달라야 합니다.")
        if op == "trend":
            out = grouped(
                df, plan.group_by + [plan.time_column], {c: "sum" for c in plan.columns}
            )
        else:
            out = df.copy()
        out = chronological(out, plan.time_column, plan.group_by)
        if op != "trend":
            for col in plan.columns:
                series = (
                    out.groupby(plan.group_by, dropna=False)[col]
                    if plan.group_by
                    else out[col]
                )
                if op == "growth_rate":
                    previous = series.shift(1)
                    out[f"{col}_growth_pct"] = (out[col] - previous).div(
                        previous.replace(0, np.nan)
                    ) * 100
                else:
                    out[f"{col}_moving_avg"] = (
                        series.transform(
                            lambda x: x.rolling(plan.window, min_periods=1).mean()
                        )
                        if plan.group_by
                        else series.rolling(plan.window, min_periods=1).mean()
                    )
            warnings.append(
                "증감률/이동평균은 시간 순서의 행 기준입니다. 같은 기간의 여러 행은 먼저 추세/집계로 확인하세요."
            )
    elif op == "correlation":
        require_numbers(df, plan.columns, 2)
        if len(df) < 3:
            raise ValueError("상관관계에는 최소 3행이 필요합니다.")
        matrix = df[plan.columns].corr()
        out = matrix.rename_axis("컬럼").reset_index()
        details = {
            "method": "Pearson",
            "pair_counts": records(
                df[plan.columns]
                .notna()
                .astype(int)
                .T.dot(df[plan.columns].notna().astype(int))
                .rename_axis("컬럼")
                .reset_index()
            ),
        }
        warnings.append(
            "상관관계는 인과관계를 의미하지 않습니다. 결측값은 쌍별 제외합니다."
        )
    elif op == "outliers":
        require_numbers(df, plan.columns)
        if len(df) < 3:
            raise ValueError("이상치 탐지에는 최소 3행이 필요합니다.")
        if len(df) < 10:
            warnings.append("표본이 10행 미만으로 이상치 판정이 불안정할 수 있습니다.")
        mask = pd.Series(False, index=df.index)
        thresholds = {}
        for col in plan.columns:
            series = df[col]
            if plan.outlier_method == "iqr":
                q1, q3 = series.quantile([0.25, 0.75])
                iqr = q3 - q1
                low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                mask |= (series < low) | (series > high)
                thresholds[col] = {"lower": float(low), "upper": float(high)}
            else:
                z = stats.zscore(series.to_numpy(dtype=float), nan_policy="omit")
                mask |= pd.Series(np.abs(z) > 3, index=df.index)
                thresholds[col] = {"z_threshold": 3}
        out = df.loc[mask]
        details = {
            "method": plan.outlier_method,
            "thresholds": thresholds,
            "outlier_count": int(mask.sum()),
        }
    elif op == "join":
        if not plan.other_dataset or plan.other_dataset not in frames:
            raise ValueError("JOIN할 두 번째 데이터셋이 필요합니다.")
        other = frames[plan.other_dataset]
        if not plan.join_keys:
            raise ValueError("JOIN KEY 없음. 두 데이터셋의 공통 키를 선택해주세요.")
        require_columns(df, plan.join_keys)
        require_columns(other, plan.join_keys)
        # Prevent a duplicate-key many-to-many Cartesian explosion before merging.
        left_counts = df.groupby(plan.join_keys, dropna=False).size().rename("l")
        right_counts = other.groupby(plan.join_keys, dropna=False).size().rename("r")
        estimated = int(
            (
                left_counts.to_frame()
                .join(right_counts, how="outer")
                .fillna(1)
                .prod(axis=1)
            ).sum()
        )
        if estimated > 1_000_000:
            raise ValueError(
                "JOIN 예상 결과가 100만 행을 넘습니다. 중복 키를 먼저 집계해주세요."
            )
        try:
            out = df.merge(
                other,
                on=plan.join_keys,
                how=plan.join_how,
                suffixes=("_left", "_right"),
                validate="many_to_many",
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "JOIN 키 타입이 서로 다릅니다. 정제 옵션을 확인해주세요."
            ) from exc
        details = {
            "join_keys": plan.join_keys,
            "join_how": plan.join_how,
            "left_rows": len(df),
            "right_rows": len(other),
            "left_duplicate_keys": int(df.duplicated(plan.join_keys).sum()),
            "right_duplicate_keys": int(other.duplicated(plan.join_keys).sum()),
        }
        if details["left_duplicate_keys"] or details["right_duplicate_keys"]:
            warnings.append(
                "중복 JOIN 키가 있습니다. 다대다 결합으로 행과 합계가 증가할 수 있습니다."
            )
        warnings.append(
            "pandas JOIN은 양쪽 결측 키도 서로 매칭합니다. 결측 키를 검토해주세요."
        )
    elif op == "missing":
        out = pd.DataFrame(
            [
                {
                    "컬럼": c,
                    "null_count": int(df[c].isna().sum()),
                    "null_ratio": float(df[c].isna().mean()),
                }
                for c in df.columns
            ]
        )
    elif op == "duplicates":
        out = df.loc[df.duplicated(subset=plan.columns or None, keep=False)]
        details = {
            "duplicate_extra_rows": int(
                df.duplicated(subset=plan.columns or None).sum()
            )
        }
    elif op == "regression":
        require_numbers(df, plan.columns, 2)
        a, b = plan.columns[:2]
        values = df[[a, b]].dropna()
        if len(values) < 3 or values[a].nunique() < 2:
            raise ValueError("회귀에는 유효한 3행과 서로 다른 X값이 필요합니다.")
        model = LinearRegression().fit(values[[a]], values[b])
        out = values.copy()
        out["prediction"] = model.predict(values[[a]])
        details = {
            "x": a,
            "y": b,
            "coefficient": float(model.coef_[0]),
            "intercept": float(model.intercept_),
            "r_squared": float(model.score(values[[a]], values[b])),
        }
        warnings.append("단순 선형 회귀는 원인이나 미래 결과를 보장하지 않습니다.")
    else:
        raise ValueError("허용되지 않은 분석입니다.")
    out = out.replace([np.inf, -np.inf], np.nan)
    return out, warnings, details


def execute_plan(plan: AnalysisPlan, frames: dict[str, pd.DataFrame]):
    out, warnings, details = compute_frame(plan, frames)
    op = plan.operation
    return {
        "operation": op,
        "plan": plan.model_dump(),
        "rows": records(out.head(500)),
        "columns": out.columns.tolist(),
        "total_rows": len(out),
        "truncated": len(out) > 500,
        "details": details,
        "warnings": warnings,
        "chart": chart_for(out, op, plan),
    }
