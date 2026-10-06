"""Connected-PC preparation only. The analysis app never runs this downloader."""

import argparse
import os
import subprocess
import hashlib
import json
import re
import shutil
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

MODEL_REPO = "Qwen/Qwen3-14B-GGUF"
MODEL_API = f"https://huggingface.co/api/models/{MODEL_REPO}?blobs=true"
CHUNK = 1024 * 1024
ROOT = Path(__file__).resolve().parent.parent


def safe_relative(value):
    if not value or "\\" in value or ":" in value or "\x00" in value:
        raise ValueError("안전하지 않은 파일 경로입니다.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in {".", ".."} for p in path.parts):
        raise ValueError("안전하지 않은 파일 경로입니다.")
    return path


def validate_download_url(url):
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    allowed = (
        host
        in {
            "github.com",
            "raw.githubusercontent.com",
            "release-assets.githubusercontent.com",
            "huggingface.co",
            "hf.co",
            "aka.ms",
            "download.visualstudio.microsoft.com",
        }
        or host.endswith(".huggingface.co")
        or host.endswith(".hf.co")
    )
    if (
        parsed.scheme != "https"
        or not allowed
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
    ):
        raise ValueError("공식 HTTPS 다운로드 주소만 허용합니다.")
    return url


class TrustedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_download_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def url_open(url, headers=None):
    validate_download_url(url)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ExcelAnalysis-Offline-Preparer/1.0", **(headers or {})},
    )
    return urllib.request.build_opener(TrustedRedirects()).open(request, timeout=60)


def fetch_json(url):
    with url_open(url) as response:
        data = response.read(5_000_001)
    if len(data) > 5_000_000:
        raise ValueError("다운로드 메타데이터가 너무 큽니다.")
    return json.loads(data)


def select_model_files(metadata):
    if metadata.get("id") != MODEL_REPO or not re.fullmatch(
        r"[a-f0-9]{40,64}", metadata.get("sha", "")
    ):
        raise ValueError("공식 Qwen 저장소와 모델 revision을 확인할 수 없습니다.")
    candidates = []
    for item in metadata.get("siblings", []):
        name = item.get("rfilename", "")
        if (
            name.lower().endswith(".gguf")
            and "qwen3-14b" in name.lower()
            and "q4_k_m" in name.lower()
        ):
            safe_relative(name)
            lfs = item.get("lfs") or {}
            digest = lfs.get("sha256", "")
            size = lfs.get("size")
            if (
                not re.fullmatch(r"[a-f0-9]{64}", digest)
                or not isinstance(size, int)
                or not 4 <= size <= 20_000_000_000
            ):
                raise ValueError(
                    "Qwen 모델의 SHA-256/크기를 확인할 수 없습니다. 검증을 생략하지 않습니다."
                )
            candidates.append(
                {
                    "name": name,
                    "sha256": digest,
                    "size": size,
                    "url": f"https://huggingface.co/{MODEL_REPO}/resolve/{metadata['sha']}/{urllib.parse.quote(name, safe='/')}?download=true",
                }
            )
    if not candidates:
        raise ValueError("공식 저장소에서 Qwen3-14B Q4_K_M GGUF를 찾지 못했습니다.")
    singles = [
        f
        for f in candidates
        if not re.search(r"-\d{5}-of-\d{5}\.gguf$", f["name"], re.I)
    ]
    if singles:
        if len(singles) != 1:
            raise ValueError(
                "Q4_K_M 모델 후보가 여러 개입니다. 배포 메타데이터 확인이 필요합니다."
            )
        return singles
    parts = [
        re.fullmatch(r"(.+)-(\d{5})-of-(\d{5})\.gguf", f["name"], re.I)
        for f in candidates
    ]
    if not all(parts):
        raise ValueError("모델 조각 파일명을 확인할 수 없습니다.")
    prefixes = {p[1] for p in parts}
    totals = {int(p[3]) for p in parts}
    if (
        len(prefixes) != 1
        or len(totals) != 1
        or sorted(int(p[2]) for p in parts) != list(range(1, next(iter(totals)) + 1))
    ):
        raise ValueError("Qwen 모델 조각이 누락되거나 서로 다른 모델입니다.")
    return sorted(candidates, key=lambda f: f["name"])


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while data := source.read(CHUNK):
            digest.update(data)
    return digest.hexdigest()


def verify_file(path, digest, size=None):
    return (
        path.is_file()
        and (size is None or path.stat().st_size == size)
        and file_hash(path) == digest
    )


def download_file(url, target, digest, size=None, opener=url_open):
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("SHA-256이 없는 파일은 다운로드하지 않습니다.")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if verify_file(target, digest, size):
        print("이미 검증된 파일 사용:", target.name, flush=True)
        return target
    if target.exists():
        raise ValueError(
            f"기존 {target.name} 파일의 해시가 다릅니다. 다른 폴더로 보존한 후 다시 실행해주세요."
        )
    partial = target.with_name(target.name + ".part")
    if partial.exists() and verify_file(partial, digest, size):
        partial.replace(target)
        return target
    offset = partial.stat().st_size if partial.exists() else 0
    if size is not None and offset >= size:
        partial.unlink()
        offset = 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    print(f"다운로드: {target.name} · 기존 {offset / 1e9:.2f}GB", flush=True)
    with opener(url, headers) as response:
        status = response.status
        if offset and status == 206:
            content_range = response.headers.get("Content-Range", "")
            if not content_range.startswith(f"bytes {offset}-"):
                raise ValueError("이어받기 응답 범위가 올바르지 않습니다.")
            mode = "ab"
        elif status == 200:
            offset = 0
            mode = "wb"
        else:
            raise ValueError(f"다운로드 서버 응답을 확인해주세요: HTTP {status}")
        last = time.monotonic()
        with partial.open(mode) as destination:
            while data := response.read(CHUNK):
                destination.write(data)
                offset += len(data)
                if offset > (size if size is not None else 4_000_000_000):
                    raise ValueError("예상 다운로드 크기를 초과했습니다.")
                if time.monotonic() - last >= 10:
                    print(
                        f"  {offset / 1e9:.2f}GB"
                        + (f" / {size / 1e9:.2f}GB" if size else ""),
                        flush=True,
                    )
                    last = time.monotonic()
    print("SHA-256 검증:", target.name, flush=True)
    if not verify_file(partial, digest, size):
        partial.unlink(missing_ok=True)
        raise ValueError("파일 무결성 검증 실패. 손상된 다운로드를 사용하지 않습니다.")
    partial.replace(target)
    return target


def extract_zip(archive, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as source:
        entries = source.infolist()
        if len(entries) > 10000 or sum(e.file_size for e in entries) > 5_000_000_000:
            raise ValueError("실행 프로그램 ZIP 크기가 비정상적입니다.")
        for entry in entries:
            relative = safe_relative(entry.filename.rstrip("/"))
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("ZIP 심볼릭 링크는 허용하지 않습니다.")
            target = destination.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError("ZIP 경로가 대상 폴더를 벗어납니다.")
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(entry) as content:
                if target.exists():
                    digest = hashlib.sha256()
                    while block := content.read(CHUNK):
                        digest.update(block)
                    if file_hash(target) != digest.hexdigest():
                        raise ValueError(
                            f"기존 실행 파일이 다릅니다: {target.name}. 새 폴더에서 준비해주세요."
                        )
                    continue
                temporary = target.with_name(target.name + ".part")
                with temporary.open("wb") as out:
                    shutil.copyfileobj(content, out, CHUNK)
                temporary.replace(target)


def server_executable(directory):
    servers = list(Path(directory).rglob("llama-server.exe"))
    if len(servers) != 1:
        raise ValueError("llama-server.exe를 정확히 하나 찾을 수 있어야 합니다.")
    return servers[0]


def package_bundle(root, destination):
    root = Path(root)
    destination = Path(destination)
    excluded = {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "test-results",
        "playwright-report",
        "releases",
        ".downloads",
    }
    with ZipFile(
        destination, "w", ZIP_DEFLATED, compresslevel=6, allowZip64=True
    ) as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if (
                not path.is_file()
                or path.is_symlink()
                or any(p in excluded for p in relative.parts)
                or path.suffix in {".log", ".pyc", ".part", ".tsbuildinfo"}
                or path.name == ".env"
                or path.resolve() == destination.resolve()
            ):
                continue
            method = (
                ZIP_STORED
                if path.suffix.lower() in {".gguf", ".whl", ".zip"}
                else ZIP_DEFLATED
            )
            archive.write(
                path,
                "excel-data-analysis-system/" + relative.as_posix(),
                compress_type=method,
            )
    with ZipFile(destination) as archive:
        if archive.testzip():
            raise ValueError("완성 ZIP 무결성 검사에 실패했습니다.")


def verify_microsoft_signature(path):
    if os.name != "nt":
        raise ValueError("AI 묶음 준비는 Windows PC에서 실행해주세요.")
    environment = dict(os.environ, KAI_REDIST_PATH=str(Path(path).resolve()))
    command = "$s=Get-AuthenticodeSignature -LiteralPath $env:KAI_REDIST_PATH; if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'CN=Microsoft Corporation(?:,|$)') { exit 1 }"
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        env=environment,
        check=True,
    )


def prepare_vc_runtime(ai):
    target = ai / "prerequisites" / "vc_redist.x64.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        partial = ai / ".downloads" / "vc_redist.x64.exe"
        partial.parent.mkdir(parents=True, exist_ok=True)
        with (
            url_open("https://aka.ms/vs/17/release/vc_redist.x64.exe") as source,
            partial.open("wb") as output,
        ):
            total = 0
            while block := source.read(CHUNK):
                total += len(block)
                if total > 100_000_000:
                    raise ValueError("Microsoft 런타임 파일 크기가 비정상적입니다.")
                output.write(block)
        verify_microsoft_signature(partial)
        partial.replace(target)
    verify_microsoft_signature(target)
    return {
        "name": "prerequisites/vc_redist.x64.exe",
        "sha256": file_hash(target),
        "publisher": "Microsoft Corporation",
        "source": "https://aka.ms/vs/17/release/vc_redist.x64.exe",
    }


def prepare(root, cpu_only=False):
    root = Path(root)
    ai = root / "local-ai"
    ai.mkdir(exist_ok=True)
    if shutil.disk_usage(root).free < 25_000_000_000:
        raise ValueError(
            "모델과 최종 ZIP을 위해 디스크 여유 공간 25GB 이상을 확보해주세요."
        )
    print("공식 Qwen 모델 메타데이터 확인 중…", flush=True)
    vc_runtime = prepare_vc_runtime(ai)
    metadata = fetch_json(MODEL_API)
    models = select_model_files(metadata)
    total = sum(f["size"] for f in models)
    print(
        f"Qwen3-14B Q4_K_M: {total / 1e9:.2f}GB · {len(models)}개 파일 (하나의 모델)",
        flush=True,
    )
    manifest = json.loads(
        (root / "scripts/ai_downloads.json").read_text(encoding="utf-8")
    )
    downloads = ai / ".downloads"
    downloads.mkdir(exist_ok=True)
    for asset in manifest["assets"]:
        if cpu_only and asset["profile"] != "cpu":
            continue
        archive = download_file(
            asset["url"], downloads / asset["name"], asset["sha256"]
        )
        extract_zip(archive, ai / asset["profile"])
    for profile in ["cpu"] if cpu_only else ["cuda", "cpu"]:
        executable = server_executable(ai / profile)
        # CUDA redistributable DLLs must be next to llama-server even with nested archives.
        for dll in (ai / profile).rglob("*.dll"):
            target = executable.parent / dll.name
            if dll == target:
                continue
            if target.exists():
                if file_hash(target) != file_hash(dll):
                    raise ValueError("DLL 파일명 충돌입니다.")
            else:
                shutil.copy2(dll, target)
    model_dir = ai / "models"
    model_dir.mkdir(exist_ok=True)
    for model in models:
        path = model_dir.joinpath(*safe_relative(model["name"]).parts)
        download_file(model["url"], path, model["sha256"], model["size"])
        with path.open("rb") as source:
            if source.read(4) != b"GGUF":
                raise ValueError("다운로드한 모델이 GGUF 형식이 아닙니다.")
    receipt = {
        "vc_runtime": vc_runtime,
        "model_repo": MODEL_REPO,
        "model_revision": metadata["sha"],
        "model_license": (metadata.get("cardData") or {}).get("license"),
        "first_model": "models/" + models[0]["name"],
        "models": models,
        "llama_release": manifest["llama_release"],
        "llama_source": manifest["source"],
        "profiles": ["cpu"] if cpu_only else ["cuda", "cpu"],
    }
    (ai / "ai-ready.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ai / "MODEL_SOURCE.txt").write_text(
        f"Model: https://huggingface.co/{MODEL_REPO}\nRevision: {metadata['sha']}\nLicense: {receipt['model_license']}\nRuntime: {manifest['source']}\n",
        encoding="utf-8",
    )
    print(
        "AI 준비 완료. 이 폴더 안에 실행 프로그램과 모델이 모두 있습니다.", flush=True
    )
    return receipt


def main():
    parser = argparse.ArgumentParser(
        description="인터넷 연결 PC에서만 실행하는 AI 일괄 준비 도구"
    )
    parser.add_argument(
        "--zip", action="store_true", help="모델 포함 단일 오프라인 ZIP도 생성"
    )
    parser.add_argument(
        "--cpu-only", action="store_true", help="CUDA 없이 CPU 실행 파일만 준비"
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        prepare(args.root, args.cpu_only)
        if args.zip:
            destination = args.root.parent / "ExcelAnalysis-with-AI.zip"
            print("모델 포함 ZIP 생성 중… 큰 파일이므로 시간이 걸립니다.", flush=True)
            package_bundle(args.root, destination)
            print("반입할 파일:", destination, flush=True)
        print(
            "망분리 PC에서 install_offline.bat → start_all.bat로 실행하세요.",
            flush=True,
        )
        return 0
    except (
        OSError,
        ValueError,
        urllib.error.URLError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as exc:
        print("AI 준비 실패:", str(exc), file=sys.stderr)
        print(
            "인터넷 연결, GitHub/Hugging Face 접근, 디스크 공간을 확인해주세요. .part 파일은 재실행 시 이어받습니다.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("다운로드 중단. 다시 실행하면 이어받기를 시도합니다.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
