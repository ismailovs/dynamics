from __future__ import annotations

from typing import Dict, Optional

import pandas as pd


def _to_numeric(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.replace(r"[^\d\.\-]", "", regex=True)
    return pd.to_numeric(text, errors="coerce")


def apply_column_mapping(raw_df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    df = raw_df.copy()
    canonical = pd.DataFrame(index=df.index)

    for field, source_col in mapping.items():
        if source_col and source_col in df.columns:
            canonical[field] = df[source_col]
        else:
            canonical[field] = pd.NA

    canonical["record_id"] = canonical.index + 1
    canonical["year_month"] = pd.NaT
    canonical["year_week"] = pd.NA
    canonical["year_quarter"] = pd.NA

    if canonical["date"].notna().any():
        parsed = pd.to_datetime(canonical["date"], errors="coerce")
        canonical["date"] = parsed
        canonical["year_month"] = parsed.dt.to_period("M").astype(str)
        canonical["year_week"] = parsed.dt.strftime("%Y-W%U")
        canonical["year_quarter"] = parsed.dt.to_period("Q").astype(str)

    if canonical["cost"].notna().any():
        canonical["cost"] = _to_numeric(canonical["cost"])
    if canonical["repair_time"].notna().any():
        canonical["repair_time"] = _to_numeric(canonical["repair_time"])

    categorical_fields = [
        "assembler",
        "checker",
        "rework",
        "job_number",
        "project",
        "customer",
        "department",
        "category",
        "root_cause",
        "severity",
        "description",
        "shift",
        "status",
        "comments",
    ]
    for field in categorical_fields:
        canonical[field] = canonical[field].fillna("Unknown").astype(str).str.strip()
        canonical[field] = canonical[field].replace("", "Unknown")

    return canonical
