from __future__ import annotations

import pandas as pd


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    numeric = df.select_dtypes(include=["number"]).dropna(axis=1, how="all")
    if numeric.empty:
        return pd.DataFrame()
    return numeric.corr(numeric_only=True)
