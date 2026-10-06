import csv
import io
from collections import Counter
import pandas as pd
from backend.models import CleanOptions
from backend.services.data_cleaner import clean_frame

MAX_ROWS = 500_000
MAX_COLUMNS = 200


def decode_file(content: bytes):
    for encoding in ["utf-8-sig", "cp949", "euc-kr"]:
        try:
            text = content.decode(encoding, errors="strict")
            if "\x00" in text:
                raise ValueError("바이너리 또는 지원하지 않는 텍스트 형식입니다.")
            return text, encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("인코딩 실패: UTF-8, CP949, EUC-KR 텍스트로 저장해주세요.")


def parse_text(
    text: str, header_start=None, header_rows=1, delimiter="tab", options=None
):
    if not text.strip():
        raise ValueError("빈 데이터입니다. Excel 범위를 복사한 뒤 붙여넣어주세요.")
    if "\x00" in text:
        raise ValueError("텍스트 데이터만 사용할 수 있습니다.")
    sep = "\t" if delimiter == "tab" else ","
    if sep not in text:
        raise ValueError(
            "TAB 구분이 감지되지 않음. 두 개 이상의 열을 복사하거나 CSV 형식을 선택해주세요."
        )
    try:
        rows = list(csv.reader(io.StringIO(text), delimiter=sep, strict=True))
    except csv.Error as exc:
        raise ValueError("텍스트 따옴표/행 구분 형식이 올바르지 않습니다.") from exc
    rows = [r for r in rows if r]  # completely empty physical lines
    if len(rows) > MAX_ROWS + 100:
        raise ValueError("최대 50만 행까지 입력할 수 있습니다.")
    width = max(map(len, rows))
    if width > MAX_COLUMNS:
        raise ValueError("최대 200열까지 입력할 수 있습니다.")
    start = (header_start - 1) if header_start else 0
    if header_start is None:
        # Excel title rows often have one populated cell followed by blanks.
        for i, row in enumerate(rows[:10]):
            if sum(bool(c.strip()) for c in row) >= 2:
                start = i
                break
    if start + header_rows >= len(rows):
        raise ValueError("Header 인식 실패: 헤더 다음에 데이터 행이 필요합니다.")
    headers = rows[start : start + header_rows]
    width = max(map(len, headers))
    names, used = [], Counter()
    for c in range(width):
        parts = []
        for h in headers:
            value = h[c].strip() if c < len(h) else ""
            if value and value not in parts:
                parts.append(value)
        base = " / ".join(parts) or f"컬럼{c + 1}"
        name = base
        while name in used:
            used[base] += 1
            name = f"{base}_{used[base] + 1}"
        used[name] += 1
        names.append(name)
    values = []
    for line, row in enumerate(rows[start + header_rows :], start + header_rows + 1):
        if len(row) != width and any(c.strip() for c in row):
            raise ValueError(
                f"{line}행의 열 수가 헤더와 다릅니다 ({len(row)} / {width}). 범위를 다시 확인해주세요."
            )
        values.append((row + [""] * width)[:width])
    raw = pd.DataFrame(values, columns=names)
    clean, info = clean_frame(raw, options or CleanOptions())
    if clean.empty or not len(clean.columns):
        raise ValueError("정제 후 분석할 데이터가 없습니다.")
    info.update({"header_start": start + 1, "header_rows": header_rows})
    return raw, clean, info
