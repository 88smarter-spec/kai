from fastapi.testclient import TestClient


def client():
    from backend.main import app

    return TestClient(app, base_url="http://127.0.0.1")


TEXT = "사업\t월\t가용인력\t소요인력\nKF-21\t1월\t210\t230\nKF-21\t2월\t215\t228\nT-50\t1월\t160\t155\nLAH\t1월\t130\t138"


def test_dataset_lifecycle_and_analysis():
    c = client()
    created = c.post("/api/datasets/paste", json={"name": "인력계획", "text": TEXT})
    assert created.status_code == 200, created.text
    identifier = created.json()["id"]
    preview = c.get(f"/api/datasets/{identifier}?limit=2").json()
    assert len(preview["preview"]) == 2 and preview["row_count"] == 4
    assert preview["profile"]["numeric_columns"] == ["가용인력", "소요인력"]
    result = c.post(
        "/api/analysis",
        json={
            "dataset": identifier,
            "operation": "difference",
            "columns": ["가용인력", "소요인력"],
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["rows"][0]["difference"] == -20
    assert result.json()["chart"]["data"]
    auto = c.post(f"/api/datasets/{identifier}/auto")
    assert auto.status_code == 200 and len(auto.json()["analyses"]) >= 3
    rename = c.patch(f"/api/datasets/{identifier}", json={"name": "변경"})
    assert rename.json()["name"] == "변경"
    cleaned = c.post(f"/api/datasets/{identifier}/clean", json={"numbers": False})
    assert cleaned.status_code == 200
    assert c.delete(f"/api/datasets/{identifier}").status_code == 200
    assert c.get(f"/api/datasets/{identifier}").status_code == 400


def test_cp949_upload_and_excel_rejection():
    c = client()
    uploaded = c.post(
        "/api/datasets/upload",
        files={"file": ("계획.tsv", TEXT.encode("cp949"), "text/tab-separated-values")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["cleaning"]["encoding"] == "cp949"
    rejected = c.post(
        "/api/datasets/upload",
        files={"file": ("secret.xlsx", b"test", "application/octet-stream")},
    )
    assert rejected.status_code == 400
    assert c.post("/api/datasets/paste", json={"text": "bad"}).status_code == 400


def test_llm_and_request_security():
    c = client()
    assert (
        c.post("/api/llm/test", json={"url": "https://example.com/v1"}).status_code
        == 400
    )
    assert c.get("/api/health", headers={"host": "evil.example"}).status_code == 403
    assert (
        c.post(
            "/api/datasets/paste",
            json={"text": TEXT},
            headers={"origin": "https://evil.example"},
        ).status_code
        == 403
    )
    missing = c.post("/api/llm/test", json={"url": "http://127.0.0.1:1/v1"})
    assert missing.status_code == 400
    assert "로컬 AI 서버" in missing.json()["detail"]
    assert (
        c.post(
            "/api/analysis",
            json={"dataset": "x", "operation": "exec", "code": "print(1)"},
        ).status_code
        == 422
    )


def test_analysis_result_can_be_saved_without_500_row_truncation():
    c = client()
    text = "키\t값\n" + "\n".join(f"A\t{i}" for i in range(600))
    identifier = c.post("/api/datasets/paste", json={"text": text}).json()["id"]
    saved = c.post(
        "/api/analysis/save",
        json={
            "name": "파생 데이터",
            "plan": {"dataset": identifier, "operation": "filter"},
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["row_count"] == 600
    c.delete("/api/datasets/" + identifier)
    c.delete("/api/datasets/" + saved.json()["id"])
