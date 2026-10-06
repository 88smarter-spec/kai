import importlib.util
import pytest


# A missing implementation is a failing requirement, not a collection error.
def test_backend_exists():
    assert importlib.util.find_spec("backend.main") is not None, (
        "FastAPI application must exist"
    )


def parser():
    from backend.services.clipboard_parser import parse_text, decode_file

    return parse_text, decode_file


def test_clipboard_cleaning():
    parse, _ = parser()
    raw, clean, info = parse(
        " 사업 \t월\t인력\t비율\t날짜\r\nKF-21\t1월\t1,200\t15%\t2027-01-01\r\nT-50\t2월\t-\tN/A\t2027-02-01\r\n\t\t\t\t"
    )
    assert len(clean) == 2
    assert clean.columns.tolist() == ["사업", "월", "인력", "비율", "날짜"]
    assert clean.iloc[0]["인력"] == 1200
    assert clean.iloc[0]["비율"] == 0.15
    assert str(clean["날짜"].dtype).startswith("datetime")
    assert len(raw) >= len(clean)


def test_encoding_and_headers():
    parse, decode = parser()
    text = "사업\t인력\nKF-21\t210"
    for encoding in ["utf-8-sig", "cp949", "euc-kr"]:
        assert decode(text.encode(encoding))[0] == text
    _, clean, _ = parse("2027년 계획\t\n사업\t인력\nKF-21\t210", header_start=2)
    assert clean.columns.tolist() == ["사업", "인력"]
    _, combined, _ = parse("계획\t계획\n사업\t인력\nKF-21\t210", header_rows=2)
    assert combined.columns.tolist() == ["계획 / 사업", "계획 / 인력"]


def test_invalid_input():
    parse, _ = parser()
    for text in ["", "hello world", "사업\t인력\nA\t1\t2"]:
        with pytest.raises(ValueError):
            parse(text)


def test_tools_and_exact_gap():
    from backend.services.analysis_engine import execute_plan
    from backend.models import AnalysisPlan
    import pandas as pd

    df = pd.DataFrame(
        {
            "사업": ["A", "A", "B"],
            "월": ["1월", "2월", "1월"],
            "가용": [210, 215, 160],
            "소요": [230, 228, 155],
        }
    )
    frames = {"one": df, "two": pd.DataFrame({"사업": ["A", "B"], "생산": [9, 3]})}

    def run(**kwargs):
        return execute_plan(AnalysisPlan(dataset="one", **kwargs), frames)

    assert (
        run(operation="difference", columns=["가용", "소요"])["rows"][0]["difference"]
        == -20
    )
    grouped = run(operation="groupby", group_by=["사업"], metrics={"가용": "sum"})
    assert grouped["rows"][0]["가용"] == 425
    assert run(operation="ratio", columns=["가용", "소요"])["rows"][0][
        "ratio"
    ] == pytest.approx(210 / 230)
    assert (
        run(operation="join", other_dataset="two", join_keys=["사업"])["total_rows"]
        == 3
    )
    for op, args in [
        ("describe", {}),
        ("aggregate", {"metrics": {"가용": "sum"}}),
        (
            "pivot",
            {"group_by": ["사업"], "pivot_column": "월", "metrics": {"가용": "sum"}},
        ),
        ("filter", {"filters": [{"column": "사업", "operator": "eq", "value": "A"}]}),
        ("sort", {"columns": ["가용"]}),
        ("top_n", {"columns": ["가용"], "n": 2}),
        ("bottom_n", {"columns": ["가용"], "n": 2}),
        (
            "growth_rate",
            {"columns": ["가용"], "time_column": "월", "group_by": ["사업"]},
        ),
        (
            "moving_average",
            {
                "columns": ["가용"],
                "time_column": "월",
                "group_by": ["사업"],
                "window": 2,
            },
        ),
        ("correlation", {"columns": ["가용", "소요"]}),
        ("outliers", {"columns": ["가용"]}),
        ("trend", {"columns": ["가용"], "time_column": "월"}),
        ("missing", {}),
        ("duplicates", {}),
        ("regression", {"columns": ["가용", "소요"]}),
    ]:
        result = run(operation=op, **args)
        assert "rows" in result and "total_rows" in result
    with pytest.raises(ValueError):
        run(operation="join", other_dataset="two", join_keys=["없는키"])
    with pytest.raises(ValueError):
        run(operation="aggregate", metrics={"사업": "sum"})
    with pytest.raises(Exception):
        AnalysisPlan(dataset="one", operation="exec", code='__import__("os")')


def test_profile():
    from backend.services.profiler import profile
    import pandas as pd

    result = profile(pd.DataFrame({"A": [1, 1, None], "B": ["가", "가", "나"]}))
    assert result["duplicates"] == 1
    assert result["columns"][0]["null_count"] == 1
    assert result["columns"][0]["mean"] == 1


def test_local_url_guard():
    from backend.services.llm_client import validate_url

    assert validate_url("http://127.0.0.1:8080/v1")
    for url in [
        "https://example.com/v1",
        "http://127.0.0.1.evil.com/v1",
        "http://localhost.evil/v1",
        "http://user:pass@localhost:8080/v1",
        "http://0.0.0.0:8080/v1",
    ]:
        with pytest.raises(ValueError):
            validate_url(url)
