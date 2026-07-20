"""Configuration loaded from CLI arguments and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str = ""
    database_path: Path = Path("youtube_trends.db")
    report_path: Path = Path("youtube_trends.xlsx")
    window_days: int = 14
    min_duration_seconds: int = 8 * 60
    max_duration_seconds: int = 60 * 60
    max_search_requests: int = 90
    daily_quota_units: int = 10_000
    target_clusters: int = 200
    min_theme_videos: int = 5
    random_state: int = 42

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=os.getenv("YOUTUBE_API_KEY", ""),
            database_path=Path(os.getenv("YT_TRENDS_DB", "youtube_trends.db")),
            report_path=Path(os.getenv("YT_TRENDS_REPORT", "youtube_trends.xlsx")),
            window_days=int(os.getenv("YT_WINDOW_DAYS", "14")),
            min_duration_seconds=int(os.getenv("YT_MIN_DURATION_SECONDS", "480")),
            max_duration_seconds=int(os.getenv("YT_MAX_DURATION_SECONDS", "3600")),
            max_search_requests=int(os.getenv("YT_MAX_SEARCH_REQUESTS", "90")),
            daily_quota_units=int(os.getenv("YT_DAILY_QUOTA_UNITS", "10000")),
            target_clusters=int(os.getenv("YT_TARGET_CLUSTERS", "200")),
            min_theme_videos=int(os.getenv("YT_MIN_THEME_VIDEOS", "5")),
            random_state=int(os.getenv("YT_RANDOM_STATE", "42")),
        )
