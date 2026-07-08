from __future__ import annotations

import pandas as pd
import plotly.express as px


def scatter_plot(df: pd.DataFrame, x_col: str, y_col: str, title: str, color: str | None = None):
    if x_col not in df.columns or y_col not in df.columns:
        return None
    working = df.copy()
    working[x_col] = pd.to_numeric(working[x_col], errors="coerce")
    working[y_col] = pd.to_numeric(working[y_col], errors="coerce")
    working = working.dropna(subset=[x_col, y_col])
    if working.empty:
        return None
    return px.scatter(working, x=x_col, y=y_col, color=color if color in working.columns else None, title=title)
