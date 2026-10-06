"""Pin wheel hashes after fetching wheels on a connected preparation machine."""

import hashlib
import re
from pathlib import Path
from email.parser import Parser
from zipfile import ZipFile

root = Path(__file__).resolve().parent.parent


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


expected = {}
for line in (root / "backend/requirements.lock.txt").read_text().splitlines():
    if "==" in line:
        name, version = line.split("==", 1)
        expected[normalize(name)] = version
found = {}
for wheel in sorted((root / "wheelhouse").glob("*.whl")):
    with ZipFile(wheel) as archive:
        metadata = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        message = Parser().parsestr(archive.read(metadata).decode())
    name = normalize(message["Name"])
    version = message["Version"]
    if expected.get(name) != version:
        continue
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    found.setdefault(name, []).append(digest)
missing = set(expected) - set(found)
if missing:
    raise SystemExit("Missing wheels: " + ", ".join(sorted(missing)))
lines = ["# Windows x64 / CPython 3.12 wheels. Generated from verified TLS downloads."]
for name, version in expected.items():
    lines.append(
        f"{name}=={version} "
        + " ".join("--hash=sha256:" + digest for digest in found[name])
    )
(root / "backend/requirements.offline.txt").write_text(
    "\n".join(lines) + "\n", encoding="utf-8"
)
print(f"Hashed wheels for {len(found)} pinned packages.")
