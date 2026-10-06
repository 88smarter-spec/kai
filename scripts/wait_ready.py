"""Launcher helper: wait for health and open the user's default browser."""

import sys
import time
import urllib.request
import webbrowser

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
health, page = sys.argv[1:3]
for _ in range(60):
    try:
        with opener.open(health, timeout=2) as response:
            if response.status != 200:
                raise OSError("Backend is not ready")
        with opener.open(page, timeout=2) as response:
            if response.status != 200:
                raise OSError("Frontend is not ready")
        webbrowser.open(page)
        break
    except OSError:
        time.sleep(1)
else:
    print(
        "서버가 시작되지 않았습니다. Backend/Frontend 창의 오류와 포트 충돌을 확인하세요."
    )
    sys.exit(1)
