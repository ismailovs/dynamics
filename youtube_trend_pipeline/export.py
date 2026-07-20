"""Excel workbook generation for trend-analysis results."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .database import Database


def export_workbook(database: Database, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    themes = [dict(row) for row in database.themes()]
    memberships = [dict(row) for row in database.theme_memberships()]
    videos = [dict(row) for row in database.videos()]
    theme_names = {theme["theme_id"]: theme["theme_name"] for theme in themes}

    top_rows = [
        {
            "Rank": rank,
            "Theme": theme["theme_name"],
            "Category": theme["parent_category"],
            "Videos": theme["video_count"],
            "Channels": theme["channel_count"],
            "Median views/day": theme["median_views_per_day"],
            "Growth": theme["median_view_velocity"],
            "Score": theme["opportunity_score"],
            "Classification": theme["classification"],
            "High confidence": bool(theme["high_confidence"]),
        }
        for rank, theme in enumerate(themes[:1000], 1)
    ]
    examples = _best_examples(memberships, theme_names)
    fastest = sorted(
        themes,
        key=lambda row: (row["median_view_velocity"], row["median_acceleration"]),
        reverse=True,
    )
    underserved = sorted(
        themes,
        key=lambda row: (
            row["median_views_per_day"] / max(row["channel_count"], 1),
            row["opportunity_score"],
        ),
        reverse=True,
    )
    methodology = _methodology_rows()

    sheets = {
        "Top 1000 Themes": top_rows,
        "Best Video Examples": examples,
        "Fastest Growing": fastest,
        "Underserved Themes": underserved,
        "Video Data": videos,
        "Methodology": methodology,
    }
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, rows in sheets.items():
            frame = pd.DataFrame(rows)
            frame = frame.map(_excel_safe) if not frame.empty else frame
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            sheet = writer.book[sheet_name]
            sheet.freeze_panes = "A2"
            if sheet.max_row > 1 and sheet.max_column > 0:
                sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                values = [len(str(cell.value or "")) for cell in column[:200]]
                sheet.column_dimensions[column[0].column_letter].width = min(
                    max(values, default=10) + 2, 50
                )
    return output_path


def _best_examples(
    memberships: list[dict[str, Any]], theme_names: dict[int, str]
) -> list[dict[str, Any]]:
    memberships.sort(
        key=lambda row: (row["theme_id"], -row["view_count"])
    )
    counts: dict[int, int] = {}
    result: list[dict[str, Any]] = []
    for row in memberships:
        theme_id = row["theme_id"]
        counts[theme_id] = counts.get(theme_id, 0) + 1
        if counts[theme_id] > 3:
            continue
        result.append(
            {
                "Theme": theme_names.get(theme_id, ""),
                "Title": row["title"],
                "Channel": row["channel_title"],
                "Published": row["published_at"],
                "Views": row["view_count"],
                "Likes": row["like_count"],
                "Comments": row["comment_count"],
                "URL": f"https://www.youtube.com/watch?v={row['video_id']}",
            }
        )
    return result


def _methodology_rows() -> list[dict[str, str]]:
    generated = datetime.now(timezone.utc).isoformat()
    details = (
        ("Generated", generated),
        ("Collection window", "Rolling 14 days (configurable)"),
        ("Duration", "8–60 minutes (configurable)"),
        (
            "Excluded",
            "Short/under-length, livestream, music, trailer, reupload, "
            "missing-statistics, non-English, and duplicate-channel-title videos",
        ),
        (
            "Immediate performance",
            "current views / max(video age hours, 1) × 24",
        ),
        (
            "Engagement",
            "(likes + comments × 2) / max(views, 1)",
        ),
        (
            "Opportunity weights",
            "25% age-adjusted views; 20% views/subscribers; 15% velocity; "
            "10% acceleration; 10% engagement; 10% channels; "
            "5% correlation; 5% consistency",
        ),
        (
            "High confidence",
            "≥5 videos, ≥3 channels, positive snapshot growth, ≤50% views "
            "from one video, and ≥70% keyword consistency",
        ),
        (
            "Clustering",
            "TF-IDF title/description/tags/category vectors and K-means; cluster "
            "count is capped by available evidence and configured target",
        ),
        (
            "Limitation",
            "YouTube exposes current public statistics, not third-party historical "
            "daily views; velocity requires snapshots collected by this system",
        ),
    )
    return [{"Item": item, "Details": details} for item, details in details]


def _excel_safe(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value
