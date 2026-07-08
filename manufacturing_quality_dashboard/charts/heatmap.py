from __future__ import annotations

import pandas as pd
import plotly.express as px


def cross_heatmap(df: pd.DataFrame, x_col: str, y_col: str, title: str):
    if x_col not in df.columns or y_col not in df.columns:
        return None
    table = pd.crosstab(df[y_col], df[x_col])
    return px.imshow(table, labels={"x": x_col, "y": y_col, "color": "count"}, title=title)
