from __future__ import annotations

import pandas as pd


def time_trend(df: pd.DataFrame, period: str) -> pd.DataFrame:
    if "date" not in df.columns:
        return pd.DataFrame(columns=["period", "count"])
    dated = df.dropna(subset=["date"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=["period", "count"])

    if period == "monthly":
        keys = dated["date"].dt.to_period("M").astype(str)
    elif period == "weekly":
        keys = dated["date"].dt.strftime("%Y-W%U")
    elif period == "daily":
        keys = dated["date"].dt.date.astype(str)
    elif period == "quarterly":
        keys = dated["date"].dt.to_period("Q").astype(str)
    else:
        raise ValueError(f"Unsupported period: {period}")

    out = keys.value_counts().sort_index().reset_index()
    out.columns = ["period", "count"]
    return out
