from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def _control_limits(series: pd.Series) -> Dict[str, float]:
    mean = float(series.mean())
    std = float(series.std(ddof=1) if len(series) > 1 else 0)
    ucl = mean + 3 * std
    lcl = max(0.0, mean - 3 * std)
    return {"mean": mean, "ucl": ucl, "lcl": lcl}


def spc_tables(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    if "date" not in df.columns:
        return {}
    dated = df.dropna(subset=["date"]).copy()
    if dated.empty:
        return {}
    dated["period"] = dated["date"].dt.to_period("M").astype(str)

    c_data = dated.groupby("period")["record_id"].count().rename("count").reset_index()
    c_limits = _control_limits(c_data["count"])
    for key, value in c_limits.items():
        c_data[key] = value
    c_data["out_of_control"] = (c_data["count"] > c_data["ucl"]) | (c_data["count"] < c_data["lcl"])

    jobs_per_period = dated.groupby("period")["job_number"].nunique().clip(lower=1)
    defects_per_period = dated.groupby("period")["record_id"].count()
    u_vals = (defects_per_period / jobs_per_period).rename("u").reset_index()
    u_limits = _control_limits(u_vals["u"])
    for key, value in u_limits.items():
        u_vals[key] = value
    u_vals["out_of_control"] = (u_vals["u"] > u_vals["ucl"]) | (u_vals["u"] < u_vals["lcl"])

    p_vals = (defects_per_period / jobs_per_period).rename("p").reset_index()
    p_limits = _control_limits(p_vals["p"])
    for key, value in p_limits.items():
        p_vals[key] = value
    p_vals["out_of_control"] = (p_vals["p"] > p_vals["ucl"]) | (p_vals["p"] < p_vals["lcl"])

    return {"c": c_data, "u": u_vals, "p": p_vals}
