"""Bundle source, prebuilt UI and Windows wheels without local data/caches."""

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent.parent
output = root.parent / "artifacts"
output.mkdir(exist_ok=True)
archive_path = output / "kai-windows-offline.zip"
files = [root / "README.md", root / ".gitignore", *root.glob("*.bat")]
for directory in ["backend", "frontend", "scripts", "samples", "docs", "wheelhouse"]:
    for path in (root / directory).rglob("*"):
        if not path.is_file():
            continue
        if any(
            part
            in {
                "node_modules",
                "__pycache__",
                ".pytest_cache",
                "test-results",
                "playwright-report",
            }
            for part in path.relative_to(root).parts
        ):
            continue
        if path.suffix in {".pyc", ".tsbuildinfo", ".log"}:
            continue
        files.append(path)
with ZipFile(archive_path, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(files):
        archive.write(path, "excel-data-analysis-system/" + str(path.relative_to(root)))
with ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    assert any(name.endswith("frontend/dist/index.html") for name in archive.namelist())
    assert len([name for name in archive.namelist() if name.endswith(".whl")]) == 33
checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
(archive_path.with_suffix(".zip.sha256")).write_text(
    checksum + "  " + archive_path.name + "\n"
)
print(
    f"{archive_path}: {archive_path.stat().st_size / 1_000_000:.1f} MB, {len(files)} files, SHA256={checksum}"
)
