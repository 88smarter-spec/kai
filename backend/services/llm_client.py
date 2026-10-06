import json
import re
from urllib.parse import urlsplit
import httpx
from backend.models import LLMSettings


def validate_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/v1"
    ):
        raise ValueError(
            "LLM API는 http://127.0.0.1:포트/v1 형식의 localhost 주소만 허용합니다."
        )
    try:
        port = parsed.port or 80
    except ValueError as exc:
        raise ValueError("LLM 포트가 올바르지 않습니다.") from exc
    host = "[::1]" if parsed.hostname == "::1" else "127.0.0.1"
    # Resolve localhost without DNS and ignore system HTTP proxies.
    return f"http://{host}:{port}/v1"


async def connection_test(settings: LLMSettings):
    base = validate_url(settings.url)
    try:
        async with httpx.AsyncClient(
            trust_env=False, follow_redirects=False, timeout=5
        ) as client:
            response = await client.get(base + "/models")
            response.raise_for_status()
            models = [m["id"] for m in response.json().get("data", [])]
            if not models:
                raise ValueError("로컬 서버가 사용 가능한 모델을 반환하지 않았습니다.")
            return {"connected": True, "models": models}
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise ValueError(
            "로컬 AI 서버에 연결할 수 없습니다. llama-server 실행과 포트를 확인해주세요."
        ) from exc


async def complete(settings, messages, json_mode=False):
    base = validate_url(settings.url)
    model = settings.model or (await connection_test(settings))["models"][0]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        async with httpx.AsyncClient(
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(180, connect=5),
        ) as client:
            response = await client.post(base + "/chat/completions", json=payload)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            if not isinstance(text, str) or len(text) > 50000:
                raise ValueError("로컬 AI 서버 응답 형식이 올바르지 않습니다.")
            return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            "로컬 AI 서버에 연결할 수 없습니다. 모델 실행 상태와 응답 형식을 확인해주세요."
        ) from exc


def grounded_text(text, evidence):
    """Conservatively reject numerical claims absent from Python evidence."""

    def facts(value):
        if isinstance(value, dict):
            return {
                k: facts(v)
                for k, v in value.items()
                if k not in {"plan", "warnings", "operation"}
            }
        if isinstance(value, list):
            return [facts(v) for v in value]
        return value

    serialized = json.dumps(facts(evidence), ensure_ascii=False, default=str)
    nums = re.findall(r"(?<!\w)[+-]?\d+(?:\.\d+)?", serialized)
    allowed = {round(float(n), 4) for n in nums}
    allowed |= {round(float(n) * 100, 4) for n in nums if abs(float(n)) <= 1}
    without_headings = re.sub(r"(?m)^\s*\d+[.)]\s*", "", text)
    for number in re.findall(r"(?<![A-Za-z])[+-]?\d[\d,]*(?:\.\d+)?", without_headings):
        value = round(float(number.replace(",", "")), 4)
        if value not in allowed:
            return None
    return text
