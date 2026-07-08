from __future__ import annotations

import pandas as pd
import plotly.express as px


def histogram(df: pd.DataFrame, column: str, title: str):
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return None
    return px.histogram(values, x=column, title=title)
