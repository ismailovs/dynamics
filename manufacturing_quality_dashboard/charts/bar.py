from __future__ import annotations

import pandas as pd
import plotly.express as px


def bar_count(df: pd.DataFrame, column: str, title: str):
    if column not in df.columns:
        return None
    table = df[column].value_counts().reset_index()
    table.columns = [column, "count"]
    return px.bar(table, x=column, y="count", title=title)
