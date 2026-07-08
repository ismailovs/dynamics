from __future__ import annotations

import pandas as pd


def employee_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if "assembler" not in df.columns:
        return pd.DataFrame()

    jobs_per_person = df.groupby("assembler")["job_number"].nunique().rename("total_jobs")
    discrepancies = df.groupby("assembler")["record_id"].count().rename("total_discrepancies")
    monthly = (
        df.groupby(["assembler", "year_month"])["record_id"]
        .count()
        .reset_index(name="count")
        .sort_values(["assembler", "count"], ascending=[True, False])
    )

    best_month = monthly.groupby("assembler").first()["year_month"].rename("best_month")
    worst_month = monthly.groupby("assembler").last()["year_month"].rename("worst_month")

    joined = pd.concat([jobs_per_person, discrepancies, best_month, worst_month], axis=1).fillna(0)
    joined["avg_defects_per_job"] = (joined["total_discrepancies"] / joined["total_jobs"]).replace(
        [float("inf")], 0
    )
    joined["trend"] = joined["best_month"].astype(str) + " -> " + joined["worst_month"].astype(str)
    joined["ranking"] = joined["total_discrepancies"].rank(method="dense", ascending=False).astype(int)
    return joined.sort_values("ranking").reset_index()
