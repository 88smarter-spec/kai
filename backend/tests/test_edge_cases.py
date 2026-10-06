import json
import pandas as pd
import pytest
from backend.models import AnalysisPlan, CleanOptions
from backend.services.analysis_engine import execute_plan
from backend.services.clipboard_parser import parse_text
from backend.services.llm_client import grounded_text


def run(df, operation, **kwargs):
    return execute_plan(
        AnalysisPlan(dataset="d", operation=operation, **kwargs), {"d": df}
    )


def test_temporal_grouping_and_zero_denominator():
    df = pd.DataFrame(
        {
            "사업": ["A"] * 3,
            "월": ["10월", "1월", "2월"],
            "인력": [30, 10, 20],
            "분모": [0, 5, 10],
        }
    )
    trend = run(df, "trend", columns=["인력"], time_column="월")
    assert [r["월"] for r in trend["rows"]] == ["1월", "2월", "10월"]
    growth = run(
        df, "growth_rate", columns=["인력"], time_column="월", group_by=["사업"]
    )
    assert [r["인력_growth_pct"] for r in growth["rows"]] == [None, 100, 50]
    moving = run(
        df,
        "moving_average",
        columns=["인력"],
        time_column="월",
        group_by=["사업"],
        window=2,
    )
    assert [r["인력_moving_avg"] for r in moving["rows"]] == [10, 15, 25]
    ratio = run(df, "ratio", columns=["인력", "분모"])
    assert ratio["rows"][0]["ratio"] is None and ratio["warnings"]


def test_quoted_clipboard_and_total_exclusion_and_identifiers():
    raw, df, info = parse_text(
        '이름\t코드\t값\n"여러\n줄"\t0012\t1,000\n소계\t0013\t2,000',
        options=CleanOptions(exclude_totals=True),
    )
    assert len(df) == 1 and len(raw) == 2
    assert df.iloc[0]["이름"] == "여러\n줄"
    assert df.iloc[0]["코드"] == "0012"
    assert df.iloc[0]["값"] == 1000
    assert info["total_candidates"] == 1
    _, duplicate, _ = parse_text("A\tA\tA_3\n1\t2\t3")
    assert len(set(duplicate.columns)) == 3


def test_numeric_grounding():
    evidence = {"gap": -20, "ratio": 0.15, "rows": 6}
    assert grounded_text("1. 결론\nGAP은 -20이며 비율은 15%입니다.", evidence)
    assert grounded_text("부족 인력은 999명입니다.", evidence) is None


def test_100k_rows_and_duckdb_aggregation():
    n = 100_000
    df = pd.DataFrame({"사업": ["A", "B"] * (n // 2), "인력": [2] * n})
    result = run(df, "groupby", group_by=["사업"], metrics={"인력": "sum"})
    assert result["rows"] == [
        {"사업": "A", "인력": 100000.0},
        {"사업": "B", "인력": 100000.0},
    ]
    preview = run(df, "filter")
    assert (
        preview["total_rows"] == n
        and len(preview["rows"]) == 500
        and preview["truncated"]
    )


def test_join_explosion_is_rejected():
    frames = {
        "a": pd.DataFrame({"키": ["x"] * 1100}),
        "b": pd.DataFrame({"키": ["x"] * 1100}),
    }
    with pytest.raises(ValueError, match="100만"):
        execute_plan(
            AnalysisPlan(
                dataset="a", operation="join", other_dataset="b", join_keys=["키"]
            ),
            frames,
        )


def test_pivot_aggregate_correlation_and_regression_values():
    df = pd.DataFrame(
        {
            "사업": ["A", "A", "B", "B"],
            "월": ["1월", "2월"] * 2,
            "x": [1, 2, 3, 4],
            "y": [2, 4, 6, 8],
        }
    )
    assert run(df, "aggregate", metrics={"x": "mean"})["rows"] == [{"x": 2.5}]
    assert run(df, "pivot", group_by=["사업"], pivot_column="월", metrics={"x": "sum"})[
        "rows"
    ] == [{"사업": "A", "1월": 1, "2월": 2}, {"사업": "B", "1월": 3, "2월": 4}]
    assert run(df, "correlation", columns=["x", "y"])["rows"][0]["y"] == 1
    regression = run(df, "regression", columns=["x", "y"])
    assert regression["details"]["coefficient"] == pytest.approx(2)
    assert regression["details"]["r_squared"] == 1


def test_ragged_data_does_not_shift_header_and_drop_rows():
    with pytest.raises(ValueError, match="열 수"):
        parse_text("사업\t인력\nA\t1\nB\t2\t잘못된열\nC\t3\t무언가")


def test_duplicate_temporal_group_and_time_is_rejected():
    df = pd.DataFrame({"월": ["1월", "2월"], "값": [1, 2]})
    with pytest.raises(ValueError, match="시간"):
        run(df, "trend", columns=["값"], time_column="월", group_by=["월"])


def test_year_and_month_order():
    df = pd.DataFrame(
        {"기간": ["2027년 10월", "2027년 2월", "2026년 12월"], "값": [3, 2, 1]}
    )
    result = run(df, "trend", columns=["값"], time_column="기간")
    assert [r["값"] for r in result["rows"]] == [1, 2, 3]


def test_dotted_dates_and_version_strings_are_not_lost():
    _, df, info = parse_text("날짜\t버전\n2026.10.06\t1.2.3\n2026.10.07\t2.3.4")
    assert str(df["날짜"].dtype).startswith("datetime")
    assert df["버전"].tolist() == ["1.2.3", "2.3.4"]
    assert df.isna().sum().sum() == 0


def test_constant_correlation_chart_is_valid_json():
    result = run(
        pd.DataFrame({"x": [1, 1, 1], "y": [1, 2, 3]}),
        "correlation",
        columns=["x", "y"],
    )
    json.dumps(result, allow_nan=False)
    assert result["chart"]["data"][0]["z"][0][0] is None


def test_trend_chart_uses_time_and_separate_groups():
    df = pd.DataFrame(
        {"사업": ["A", "A", "B", "B"], "월": ["1월", "2월"] * 2, "값": [1, 2, 3, 4]}
    )
    result = run(df, "trend", group_by=["사업"], time_column="월", columns=["값"])
    data = result["chart"]["data"]
    assert len(data) == 2
    assert data[0]["x"] == ["1월", "2월"] and data[1]["x"] == ["1월", "2월"]
    assert data[0]["y"] == [1, 2] and data[1]["y"] == [3, 4]
    numeric = run(
        pd.DataFrame({"월": [10, 20], "값": [5, 6]}),
        "trend",
        time_column="월",
        columns=["값"],
    )
    assert numeric["chart"]["data"][0]["x"] == [10, 20]
    assert len(numeric["chart"]["data"]) == 1


def test_llm_plan_parameters_are_not_numerical_evidence():
    assert (
        grounded_text(
            "부족 인력은 999명입니다.",
            {"plan": {"n": 999}, "rows": [{"difference": -20}]},
        )
        is None
    )
