from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def control_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str):
    if df.empty or x_col not in df.columns or y_col not in df.columns:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], mode="lines+markers", name=y_col))
    for line_name in ("mean", "ucl", "lcl"):
        if line_name in df.columns:
            fig.add_trace(go.Scatter(x=df[x_col], y=df[line_name], mode="lines", name=line_name.upper()))
    if "out_of_control" in df.columns:
        flagged = df[df["out_of_control"]]
        fig.add_trace(
            go.Scatter(
                x=flagged[x_col],
                y=flagged[y_col],
                mode="markers",
                marker=dict(color="red", size=10),
                name="Out of control",
            )
        )
    fig.update_layout(title=title, xaxis_title=x_col, yaxis_title=y_col)
    return fig
