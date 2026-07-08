from __future__ import annotations

import pandas as pd


def department_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if "department" not in df.columns:
        return pd.DataFrame()
    grouped = (
        df.groupby("department")
        .agg(
            total_defects=("record_id", "count"),
            average_defects=("record_id", "mean"),
            monthly_trend=("year_month", "nunique"),
        )
        .reset_index()
    )
    return grouped.sort_values("total_defects", ascending=False)
