"""Trusted Windows launcher only; never called by an LLM or analysis tool."""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def inside(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("AI 파일 경로가 폴더를 벗어납니다.")
    return path


def launch_commands(root, environment):
    ai = Path(root) / "local-ai"
    try:
        manifest = json.loads((ai / "ai-ready.json").read_text(encoding="utf-8"))
        model = inside(ai, manifest["first_model"])
        for item in manifest["models"]:
            path = inside(ai, "models/" + item["name"])
            if not path.is_file() or path.stat().st_size != item["size"]:
                raise ValueError(
                    "모델 파일이 없거나 크기가 다릅니다. AI 준비를 다시 실행해주세요."
                )
        with model.open("rb") as stream:
            if stream.read(4) != b"GGUF":
                raise ValueError("모델 GGUF 형식이 올바르지 않습니다.")
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError(
            "모델 준비 기록이 없습니다. 인터넷 연결 PC에서 AI포함_묶음만들기.bat를 먼저 실행해주세요."
        ) from exc
    mode = environment.get("KAI_AI_MODE", "auto")
    if mode not in {"auto", "cuda", "cpu"}:
        raise ValueError("KAI_AI_MODE는 auto/cuda/cpu 중 하나여야 합니다.")
    try:
        layers = int(environment.get("KAI_GPU_LAYERS", "20"))
        context = int(environment.get("KAI_CONTEXT", "8192"))
        if not 0 <= layers <= 99 or not 512 <= context <= 32768:
            raise ValueError
    except ValueError as exc:
        raise ValueError(
            "GPU layer(0~99) / context(512~32768) 설정을 확인해주세요."
        ) from exc
    commands = []
    profiles = (
        ["cpu"] if mode == "cpu" else ["cuda", "cpu"] if mode == "auto" else ["cuda"]
    )
    for profile in profiles:
        servers = list((ai / profile).rglob("llama-server.exe"))
        if len(servers) != 1:
            continue
        executable = servers[0].resolve()
        if not executable.is_relative_to(ai.resolve()):
            raise ValueError("AI 실행 파일 경로가 올바르지 않습니다.")
        commands.append(
            [
                str(executable),
                "-m",
                str(model),
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
                "-c",
                str(context),
                "-ngl",
                str(layers if profile == "cuda" else 0),
                "--parallel",
                "1",
                "--alias",
                "qwen-local",
            ]
        )
    if not commands:
        raise ValueError(
            "AI 실행 프로그램이 없습니다. 준비 스크립트를 다시 실행해주세요."
        )
    return commands


def existing_server():
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("http://127.0.0.1:8080/v1/models", timeout=2) as response:
            return bool(json.loads(response.read(100000)).get("data"))
    except (OSError, ValueError):
        return False


def main():
    try:
        if existing_server():
            print("로컬 AI 서버가 이미 실행 중입니다.")
            return 0
        commands = launch_commands(ROOT, os.environ)
        for i, command in enumerate(commands):
            if i:
                print(
                    "GPU 실행 실패. CPU 모드로 다시 시작합니다. 처리 속도는 느릴 수 있습니다.",
                    flush=True,
                )
            print("로컬 Qwen 시작 중. 이 창을 유지하세요.", flush=True)
            try:
                result = subprocess.run(
                    command, cwd=Path(command[0]).parent, check=False
                )
                if result.returncode == 0:
                    return 0
            except OSError as exc:
                print("AI 실행 오류:", exc, flush=True)
        print("AI 실행 실패. GPU 드라이버, Windows x64, 모델과 서버 로그를 확인하세요.")
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
