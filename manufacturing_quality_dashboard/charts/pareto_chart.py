from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from analytics.pareto import pareto_table


def pareto_figure(df: pd.DataFrame, column: str, title: str):
    table = pareto_table(df, column)
    if table.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(x=table[column], y=table["count"], name="Count"))
    fig.add_trace(
        go.Scatter(
            x=table[column],
            y=table["cumulative_percentage"],
            mode="lines+markers",
            name="Cumulative %",
            yaxis="y2",
        )
    )
    fig.update_layout(
        title=title,
        yaxis=dict(title="Count"),
        yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 100]),
    )
    return fig
