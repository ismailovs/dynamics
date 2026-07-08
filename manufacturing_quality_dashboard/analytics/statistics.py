from __future__ import annotations

from typing import Dict

import pandas as pd


def descriptive_stats(series: pd.Series) -> Dict[str, float]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {}
    mode_value = clean.mode().iloc[0] if not clean.mode().empty else None
    return {
        "count": float(clean.count()),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "mode": float(mode_value) if mode_value is not None else 0.0,
        "min": float(clean.min()),
        "max": float(clean.max()),
        "std": float(clean.std(ddof=1) if clean.count() > 1 else 0.0),
        "variance": float(clean.var(ddof=1) if clean.count() > 1 else 0.0),
    }


def frequency_percentages(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "count", "percentage"])
    grouped = df[column].fillna("Unknown").astype(str).value_counts(dropna=False).reset_index()
    grouped.columns = [column, "count"]
    grouped["percentage"] = (grouped["count"] / grouped["count"].sum() * 100).round(2)
    return grouped
