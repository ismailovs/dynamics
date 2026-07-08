from __future__ import annotations

import pandas as pd


def checker_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if "checker" not in df.columns:
        return pd.DataFrame()
    inspections = df.groupby("checker")["job_number"].nunique().rename("inspections_performed")
    findings = df.groupby("checker")["record_id"].count().rename("defects_found")
    out = pd.concat([inspections, findings], axis=1).fillna(0)
    out["average_findings"] = (out["defects_found"] / out["inspections_performed"]).replace(
        [float("inf")], 0
    )
    out["ranking"] = out["defects_found"].rank(method="dense", ascending=False).astype(int)
    return out.sort_values("ranking").reset_index()
