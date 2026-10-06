"""Real localhost HTTP protocol tests; these do not claim real model quality."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.tests.test_api import TEXT


@pytest.fixture
def local_llm():
    state = {
        "plan": None,
        "answer": "결론: 가용인력 대비 소요인력 GAP은 -20입니다. 추가 데이터 확인 필요.",
        "requests": [],
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"data": [{"id": "qwen-test"}]}).encode())

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append(payload)
            content = (
                json.dumps(state["plan"], ensure_ascii=False)
                if payload.get("response_format")
                else state["answer"]
            )
            response = {"choices": [{"message": {"content": content}}]}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield state, {"url": f"http://127.0.0.1:{server.server_port}/v1"}
    server.shutdown()
    server.server_close()
    thread.join()


def test_plan_execution_interpretation_and_hallucination_guard(local_llm):
    state, settings = local_llm
    c = TestClient(app, base_url="http://127.0.0.1")
    identifier = c.post(
        "/api/datasets/paste", json={"name": "LLM 테스트", "text": TEXT}
    ).json()["id"]
    state["plan"] = {
        "dataset": identifier,
        "operation": "difference",
        "columns": ["가용인력", "소요인력"],
    }
    assert c.post("/api/llm/test", json=settings).json()["connected"]
    body = {"dataset": identifier, "question": "GAP을 분석해줘", "settings": settings}
    planned = c.post("/api/chat", json=body)
    assert planned.status_code == 200 and planned.json()["stage"] == "plan"
    interpreted = c.post(
        "/api/chat", json={**body, "execute": True, "plan": planned.json()["plan"]}
    )
    assert interpreted.status_code == 200, interpreted.text
    assert interpreted.json()["result"]["rows"][0]["difference"] == -20
    assert "-20" in interpreted.json()["answer"]
    assert interpreted.json()["warning"] is None
    # Planner sees metadata, not copied business rows.
    context = json.loads(state["requests"][0]["messages"][1]["content"])
    assert "rows" not in context["datasets"][0]
    state["answer"] = "부족 인력은 999명이며 모두 채용해야 합니다."
    rejected = c.post(
        "/api/chat", json={**body, "execute": True, "plan": planned.json()["plan"]}
    )
    assert "표시하지 않았습니다" in rejected.json()["answer"]
    assert "999" not in rejected.json()["answer"]
    state["plan"] = {"dataset": identifier, "operation": "exec", "code": "dangerous"}
    assert c.post("/api/chat", json=body).status_code == 400
    c.delete("/api/datasets/" + identifier)


def test_llm_down_preserves_python_analysis_and_report():
    c = TestClient(app, base_url="http://127.0.0.1")
    identifier = c.post("/api/datasets/paste", json={"text": TEXT}).json()["id"]
    base = {
        "dataset": identifier,
        "question": "분석",
        "settings": {"url": "http://127.0.0.1:1/v1"},
    }
    result = c.post(
        "/api/chat",
        json={
            **base,
            "execute": True,
            "plan": {
                "dataset": identifier,
                "operation": "difference",
                "columns": ["가용인력", "소요인력"],
            },
        },
    )
    assert (
        result.status_code == 200
        and result.json()["result"]["rows"][0]["difference"] == -20
    )
    assert result.json()["warning"]
    report = c.post("/api/chat", json={**base, "report": True})
    assert report.status_code == 200 and report.json()["evidence"]["summary"]
    c.delete("/api/datasets/" + identifier)
