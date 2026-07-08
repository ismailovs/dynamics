from __future__ import annotations

import pandas as pd


def pareto_table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "count", "cumulative_percentage"])
    table = df[column].fillna("Unknown").astype(str).value_counts().reset_index()
    table.columns = [column, "count"]
    total = table["count"].sum()
    table["cumulative_percentage"] = (table["count"].cumsum() / total * 100).round(2)
    return table
