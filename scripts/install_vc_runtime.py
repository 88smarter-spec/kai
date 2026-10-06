"""Install the verified bundled Windows AI prerequisite, with Windows UAC."""

import json
import os
import subprocess
from pathlib import Path
from prepare_ai_bundle import file_hash, verify_microsoft_signature


def main():
    ai = Path(__file__).resolve().parent.parent / "local-ai"
    receipt = json.loads((ai / "ai-ready.json").read_text(encoding="utf-8"))
    path = ai / "prerequisites/vc_redist.x64.exe"
    if file_hash(path) != receipt["vc_runtime"]["sha256"]:
        raise ValueError("Microsoft 런타임 파일 SHA-256이 다릅니다.")
    verify_microsoft_signature(path)
    command = "$p=Start-Process -FilePath $env:KAI_REDIST_PATH -ArgumentList '/install','/passive','/norestart' -Verb RunAs -Wait -PassThru; if ($p.ExitCode -in 0,3010,1638) { exit 0 }; exit 1"
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        env=dict(os.environ, KAI_REDIST_PATH=str(path.resolve())),
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print("Microsoft 런타임 설치 실패:", exc)
        raise SystemExit(1)
