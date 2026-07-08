from __future__ import annotations

import pandas as pd
import plotly.express as px


def pie_distribution(df: pd.DataFrame, column: str, title: str):
    if column not in df.columns:
        return None
    table = df[column].value_counts().reset_index()
    table.columns = [column, "count"]
    return px.pie(table, names=column, values="count", title=title)
