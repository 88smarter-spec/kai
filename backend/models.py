from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class CleanOptions(BaseModel):
    empty_rows: bool = True
    empty_columns: bool = True
    exclude_totals: bool = False
    numbers: bool = True
    dates: bool = True
    percentages: bool = True


class PasteRequest(BaseModel):
    name: str = Field(default="새 데이터셋", min_length=1, max_length=100)
    text: str = Field(max_length=50_000_000)
    header_start: int | None = Field(default=None, ge=1, le=100)
    header_rows: int = Field(default=1, ge=1, le=3)
    delimiter: Literal["tab", "comma"] = "tab"
    options: CleanOptions = Field(default_factory=CleanOptions)


class FilterRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: str
    operator: Literal["eq", "ne", "gt", "ge", "lt", "le", "contains", "in", "is_null"]
    value: Any = None


Operation = Literal[
    "describe",
    "groupby",
    "aggregate",
    "pivot",
    "filter",
    "sort",
    "top_n",
    "bottom_n",
    "difference",
    "ratio",
    "growth_rate",
    "moving_average",
    "correlation",
    "outliers",
    "trend",
    "join",
    "missing",
    "duplicates",
    "regression",
]
Aggregation = Literal["sum", "mean", "median", "min", "max", "count", "std"]


class AnalysisPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str
    operation: Operation
    columns: list[str] = Field(default_factory=list, max_length=20)
    group_by: list[str] = Field(default_factory=list, max_length=5)
    metrics: dict[str, Aggregation] = Field(default_factory=dict, max_length=20)
    filters: list[FilterRule] = Field(default_factory=list, max_length=10)
    n: int = Field(default=10, ge=1, le=500)
    ascending: bool = False
    time_column: str | None = None
    pivot_column: str | None = None
    window: int = Field(default=3, ge=1, le=100)
    other_dataset: str | None = None
    join_keys: list[str] = Field(default_factory=list, max_length=5)
    join_how: Literal["inner", "left", "outer"] = "inner"
    outlier_method: Literal["iqr", "zscore"] = "iqr"


class LLMSettings(BaseModel):
    url: str = "http://127.0.0.1:8080/v1"
    model: str = ""
    temperature: float = Field(default=0.2, ge=0, le=1)
    max_tokens: int = Field(default=2048, ge=128, le=8192)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    dataset: str
    settings: LLMSettings = Field(default_factory=LLMSettings)
    report: bool = False
    execute: bool = False
    plan: AnalysisPlan | None = None
