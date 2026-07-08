from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest


def anomaly_scores(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    working = df.copy()
    feature_df = pd.DataFrame(index=working.index)
    numeric_columns = ["cost", "repair_time"]
    for col in numeric_columns:
        if col in working.columns:
            feature_df[col] = pd.to_numeric(working[col], errors="coerce").fillna(0)
        else:
            feature_df[col] = 0

    counts = working.groupby("job_number")["record_id"].transform("count")
    feature_df["defects_per_job"] = counts.fillna(0)
    if feature_df.empty:
        return pd.DataFrame()

    model = IsolationForest(contamination=contamination, random_state=42)
    preds = model.fit_predict(feature_df)
    scores = model.decision_function(feature_df)
    result = working[["job_number", "assembler", "department", "cost", "repair_time", "record_id"]].copy()
    result["anomaly_flag"] = preds == -1
    result["anomaly_score"] = scores
    return result.sort_values("anomaly_score")
