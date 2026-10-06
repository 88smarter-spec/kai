import json
import pandas as pd
import numpy as np


def records(df: pd.DataFrame):
    # JSON roundtrip handles NaN, timestamps and numpy scalars consistently.
    return json.loads(
        df.to_json(orient="records", date_format="iso", force_ascii=False)
    )


def scalar(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def profile(df):
    result = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "duplicates": int(df.duplicated().sum()),
        "null_count": int(df.isna().sum().sum()),
        "numeric_columns": [],
        "categorical_columns": [],
        "date_columns": [],
        "columns": [],
    }
    for name in df.columns:
        series = df[name]
        numeric = pd.api.types.is_numeric_dtype(series)
        dates = pd.api.types.is_datetime64_any_dtype(series)
        result[
            "numeric_columns"
            if numeric
            else "date_columns"
            if dates
            else "categorical_columns"
        ].append(name)
        counts = series.value_counts(dropna=True).head(5)
        item = {
            "name": name,
            "dtype": str(series.dtype),
            "unique": int(series.nunique()),
            "null_count": int(series.isna().sum()),
            "null_ratio": float(series.isna().mean()) if len(df) else 0,
            "representative": scalar(counts.index[0]) if len(counts) else None,
            "top_values": [
                {"value": scalar(k), "count": int(v)} for k, v in counts.items()
            ],
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
        }
        if numeric or dates:
            item.update(min=scalar(series.min()), max=scalar(series.max()))
        if numeric:
            item.update(
                mean=scalar(series.mean()),
                median=scalar(series.median()),
                std=scalar(series.std()),
            )
        result["columns"].append(item)
    return result
