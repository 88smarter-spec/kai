import re
import pandas as pd
from backend.models import CleanOptions

MISSING = {"", "-", "n/a", "na", "null", "none"}
TOTAL = re.compile(r"^(합계|소계|총계|총합|total|subtotal)(\s|$)", re.I)


def clean_frame(raw: pd.DataFrame, options: CleanOptions):
    df = raw.copy(deep=True)
    warnings = []
    for col in df.columns:
        df[col] = df[col].map(lambda x: str(x).strip() if pd.notna(x) else None)
        df[col] = df[col].map(
            lambda x: None if x is None or x.lower() in MISSING else x
        )
    if options.empty_rows:
        df = df.dropna(how="all")
    if options.empty_columns:
        df = df.dropna(axis=1, how="all")
    total_mask = df.apply(
        lambda col: col.map(
            lambda x: bool(TOTAL.match(x)) if isinstance(x, str) else False
        )
    ).any(axis=1)
    totals = int(total_mask.sum())
    if options.exclude_totals:
        df = df.loc[~total_mask]
    for col in df.columns:
        present = df[col].dropna()
        if present.empty:
            continue
        strings = present.astype(str)
        numeric_pattern = (
            r"^[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$"
        )
        percents = strings.str.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)\s*%")
        if options.percentages and percents.all():
            df[col] = (
                pd.to_numeric(
                    df[col].str.replace("%", "", regex=False), errors="coerce"
                )
                / 100
            )
        elif options.numbers and strings.str.match(numeric_pattern).all():
            # Keep leading-zero identifiers as text.
            if strings.str.match(r"^0\d+$").any():
                warnings.append(
                    f"{col}: 앞자리 0이 있는 값은 식별자로 보아 문자로 유지했습니다."
                )
            else:
                converted = pd.to_numeric(
                    df[col].str.replace(",", "", regex=False), errors="coerce"
                )
                if converted.notna().sum() == len(present):
                    df[col] = converted
                else:
                    warnings.append(f"{col}: 숫자 변환 실패로 원문을 유지했습니다.")
        elif (
            options.dates
            and strings.str.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}(?:\s.*)?$").all()
        ):
            parsed = pd.to_datetime(df[col], format="mixed", errors="coerce")
            if parsed.notna().sum() == len(present):
                df[col] = parsed
            else:
                warnings.append(
                    f"{col}: 유효하지 않은 날짜가 있어 문자로 유지했습니다."
                )
        elif options.numbers and strings.str.match(numeric_pattern).any():
            warnings.append(f"{col}: 숫자와 문자가 섞여 숫자 변환 없이 유지했습니다.")
    return df.reset_index(drop=True), {
        "total_candidates": totals,
        "removed_rows": len(raw) - len(df),
        "removed_columns": len(raw.columns) - len(df.columns),
        "warnings": warnings,
    }
