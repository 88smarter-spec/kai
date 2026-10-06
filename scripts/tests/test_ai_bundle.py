import hashlib
import io
import json
from zipfile import ZipFile
import pytest


def builder():
    from scripts import prepare_ai_bundle

    return prepare_ai_bundle


def test_model_selection_requires_official_q4_hashes_and_complete_shards():
    b = builder()

    def file(name):
        return {"rfilename": name, "lfs": {"sha256": "a" * 64, "size": 123}}

    metadata = {
        "id": "Qwen/Qwen3-14B-GGUF",
        "sha": "b" * 40,
        "siblings": [
            file("Qwen3-14B-Q4_K_M-00001-of-00002.gguf"),
            file("Qwen3-14B-Q4_K_M-00002-of-00002.gguf"),
            file("Qwen3-14B-Q8_0.gguf"),
        ],
    }
    model = b.select_model_files(metadata)
    assert len(model) == 2 and model[0]["name"].endswith("00001-of-00002.gguf")
    assert "/resolve/" + "b" * 40 + "/" in model[0]["url"]
    with pytest.raises(ValueError, match="조각"):
        b.select_model_files({**metadata, "siblings": metadata["siblings"][:1]})
    bad = {**metadata, "siblings": [{"rfilename": "Qwen3-14B-Q4_K_M.gguf"}]}
    with pytest.raises(ValueError, match="SHA"):
        b.select_model_files(bad)


def test_bundle_security_guards_and_safe_extraction(tmp_path):
    b = builder()
    for url in [
        "http://github.com/a",
        "https://github.com.evil/a",
        "https://evil.test/file",
        "file:///a",
    ]:
        with pytest.raises(ValueError):
            b.validate_download_url(url)
    assert b.validate_download_url("https://cdn-lfs.hf.co/file")
    with pytest.raises(ValueError):
        b.safe_relative("../secret")
    with pytest.raises(ValueError):
        b.safe_relative("C:/secret")
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("../outside.exe", b"bad")
    with pytest.raises(ValueError):
        b.extract_zip(archive, tmp_path / "out")
    assert not (tmp_path / "outside.exe").exists()


def test_checksum_and_zip_packaging(tmp_path):
    b = builder()
    target = tmp_path / "model.gguf"
    target.write_bytes(b"GGUFtest")
    assert b.verify_file(target, hashlib.sha256(b"GGUFtest").hexdigest(), 8)
    assert not b.verify_file(target, "0" * 64, 8)
    (tmp_path / "local-ai/models").mkdir(parents=True)
    (tmp_path / "local-ai/models/m.gguf").write_bytes(b"GGUFtest")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv/secret").write_text("exclude")
    (tmp_path / "README.md").write_text("test")
    (tmp_path / "releases").mkdir()
    (tmp_path / "releases/old.zip").write_bytes(b"exclude")
    out = tmp_path.parent / (tmp_path.name + ".zip")
    b.package_bundle(tmp_path, out)
    with ZipFile(out) as z:
        names = z.namelist()
        assert any(n.endswith("local-ai/models/m.gguf") for n in names)
        assert not any(".venv" in n or "releases/" in n for n in names)
        assert z.testzip() is None


def test_launcher_selects_relative_models_and_cpu_fallback(tmp_path):
    from scripts.launch_llm import launch_commands

    for directory in ["cuda", "cpu", "models"]:
        (tmp_path / "local-ai" / directory).mkdir(parents=True)
    for profile in ["cuda", "cpu"]:
        (tmp_path / "local-ai" / profile / "llama-server.exe").write_bytes(b"MZtest")
    (tmp_path / "local-ai/models/model.gguf").write_bytes(b"GGUFtest")
    manifest = {
        "first_model": "models/model.gguf",
        "models": [{"name": "model.gguf", "size": 8}],
    }
    (tmp_path / "local-ai/ai-ready.json").write_text(json.dumps(manifest))
    commands = launch_commands(tmp_path, {})
    assert len(commands) == 2
    assert str(tmp_path / "local-ai/models/model.gguf") in commands[0]
    assert commands[0][commands[0].index("--host") + 1] == "127.0.0.1"
    assert commands[0][commands[0].index("-ngl") + 1] == "20"
    assert commands[1][commands[1].index("-ngl") + 1] == "0"
    cpu = launch_commands(tmp_path, {"KAI_AI_MODE": "cpu"})
    assert len(cpu) == 1 and "cpu" in cpu[0][0]
    (tmp_path / "local-ai/models/model.gguf").write_bytes(b"bad")
    with pytest.raises(ValueError, match="모델"):
        launch_commands(tmp_path, {})


def test_download_resume_hash_rejection_and_verified_reuse(tmp_path):
    b = builder()
    content = b"GGUFmodel-content"
    digest = hashlib.sha256(content).hexdigest()
    target = tmp_path / "model.gguf"
    target.with_name(target.name + ".part").write_bytes(content[:4])
    calls = []

    class Response(io.BytesIO):
        status = 206
        headers = {"Content-Range": f"bytes 4-{len(content) - 1}/{len(content)}"}

    def open_response(url, headers):
        calls.append(headers)
        return Response(content[4:])

    b.download_file(
        "https://huggingface.co/model",
        target,
        digest,
        len(content),
        opener=open_response,
    )
    assert target.read_bytes() == content
    assert calls == [{"Range": "bytes=4-"}]
    b.download_file(
        "https://huggingface.co/model",
        target,
        digest,
        len(content),
        opener=open_response,
    )
    assert len(calls) == 1
    target.unlink()

    class FullResponse(io.BytesIO):
        status = 200
        headers = {}

    with pytest.raises(ValueError, match="무결성"):
        b.download_file(
            "https://huggingface.co/model",
            target,
            digest,
            len(content),
            opener=lambda u, h: FullResponse(b"x" * len(content)),
        )
    assert not target.exists() and not target.with_name(target.name + ".part").exists()
    target.with_name(target.name + ".part").write_bytes(content[:4])
    b.download_file(
        "https://huggingface.co/model",
        target,
        digest,
        len(content),
        opener=lambda u, h: FullResponse(content),
    )
    assert target.read_bytes() == content


def test_extraction_retries_after_interruption(tmp_path, monkeypatch):
    b = builder()
    archive = tmp_path / "runtime.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("llama-server.exe", b"MZcomplete")
    original = b.shutil.copyfileobj

    def interrupted(source, destination, length):
        destination.write(b"MZ")
        raise OSError("simulated interruption")

    monkeypatch.setattr(b.shutil, "copyfileobj", interrupted)
    with pytest.raises(OSError):
        b.extract_zip(archive, tmp_path / "runtime")
    assert not (tmp_path / "runtime/llama-server.exe").exists()
    monkeypatch.setattr(b.shutil, "copyfileobj", original)
    b.extract_zip(archive, tmp_path / "runtime")
    assert (tmp_path / "runtime/llama-server.exe").read_bytes() == b"MZcomplete"


def test_vc_runtime_requires_signature_before_finalizing(tmp_path, monkeypatch):
    b = builder()
    monkeypatch.setattr(b, "url_open", lambda url: io.BytesIO(b"MZredist"))

    def reject(path):
        raise ValueError("signature invalid")

    monkeypatch.setattr(b, "verify_microsoft_signature", reject)
    with pytest.raises(ValueError, match="signature"):
        b.prepare_vc_runtime(tmp_path)
    assert not (tmp_path / "prerequisites/vc_redist.x64.exe").exists()
    checked = []
    monkeypatch.setattr(
        b, "verify_microsoft_signature", lambda path: checked.append(path)
    )
    receipt = b.prepare_vc_runtime(tmp_path)
    assert receipt["sha256"] == hashlib.sha256(b"MZredist").hexdigest()
    assert len(checked) == 2
