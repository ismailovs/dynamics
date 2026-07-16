"""SQLite persistence for videos, snapshots, themes, and memberships."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import date, datetime, timezone
from pathlib import Path

from .filtering import title_fingerprint
from .models import Theme, Video

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    title_fingerprint TEXT NOT NULL,
    description TEXT,
    channel_id TEXT,
    channel_title TEXT,
    published_at TIMESTAMP,
    duration_seconds INTEGER,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    subscriber_count INTEGER,
    tags TEXT,
    language TEXT,
    thumbnail_url TEXT,
    category TEXT,
    discovery_category TEXT,
    collected_at TIMESTAMP,
    UNIQUE(channel_id, title_fingerprint)
);

CREATE TABLE IF NOT EXISTS video_snapshots (
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    PRIMARY KEY (video_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS themes (
    theme_id INTEGER PRIMARY KEY,
    theme_name TEXT,
    parent_category TEXT,
    video_count INTEGER,
    channel_count INTEGER,
    median_views REAL,
    median_views_per_day REAL,
    median_view_subscriber_ratio REAL,
    median_view_velocity REAL,
    median_acceleration REAL,
    median_engagement REAL,
    correlation_score REAL,
    consistency REAL,
    opportunity_score REAL,
    classification TEXT,
    high_confidence INTEGER,
    calculated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS theme_videos (
    theme_id INTEGER NOT NULL REFERENCES themes(theme_id) ON DELETE CASCADE,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
    PRIMARY KEY (theme_id, video_id)
);

CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_video_date
ON video_snapshots(video_id, snapshot_date);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def existing_title_keys(self) -> set[tuple[str, str]]:
        rows = self.connection.execute(
            "SELECT channel_id, title_fingerprint FROM videos"
        )
        return {(row["channel_id"], row["title_fingerprint"]) for row in rows}

    def upsert_videos(
        self, videos: Iterable[Video], collected_at: datetime | None = None
    ) -> int:
        collected_at = collected_at or datetime.now(timezone.utc)
        count = 0
        with self.connection:
            for video in videos:
                values = (
                    video.video_id,
                    video.title,
                    title_fingerprint(video.title),
                    video.description,
                    video.channel_id,
                    video.channel_title,
                    video.published_at.isoformat(),
                    video.duration_seconds,
                    video.view_count,
                    video.like_count,
                    video.comment_count,
                    video.subscriber_count,
                    json.dumps(video.tags, ensure_ascii=False),
                    video.language,
                    video.thumbnail_url,
                    video.category,
                    video.discovery_category,
                    collected_at.isoformat(),
                )
                cursor = self.connection.execute(
                    """
                    INSERT INTO videos VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    ON CONFLICT(video_id) DO UPDATE SET
                        title=excluded.title,
                        title_fingerprint=excluded.title_fingerprint,
                        description=excluded.description,
                        channel_title=excluded.channel_title,
                        view_count=excluded.view_count,
                        like_count=excluded.like_count,
                        comment_count=excluded.comment_count,
                        subscriber_count=excluded.subscriber_count,
                        tags=excluded.tags,
                        language=excluded.language,
                        thumbnail_url=excluded.thumbnail_url,
                        category=excluded.category,
                        discovery_category=excluded.discovery_category,
                        collected_at=excluded.collected_at
                    """,
                    values,
                )
                count += cursor.rowcount
        return count

    def snapshot(
        self,
        statistics: dict[str, tuple[int, int, int]] | None = None,
        snapshot_date: date | None = None,
    ) -> int:
        snapshot_date = snapshot_date or datetime.now(timezone.utc).date()
        if statistics is None:
            rows = self.connection.execute(
                "SELECT video_id, view_count, like_count, comment_count FROM videos"
            )
            statistics = {
                row["video_id"]: (
                    row["view_count"],
                    row["like_count"],
                    row["comment_count"],
                )
                for row in rows
            }
        with self.connection:
            for video_id, (views, likes, comments) in statistics.items():
                if min(views, likes, comments) < 0:
                    continue
                self.connection.execute(
                    """
                    UPDATE videos
                    SET view_count=?, like_count=?, comment_count=?
                    WHERE video_id=?
                    """,
                    (views, likes, comments, video_id),
                )
                self.connection.execute(
                    """
                    INSERT INTO video_snapshots
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(video_id, snapshot_date) DO UPDATE SET
                        view_count=excluded.view_count,
                        like_count=excluded.like_count,
                        comment_count=excluded.comment_count
                    """,
                    (video_id, snapshot_date.isoformat(), views, likes, comments),
                )
        return len(statistics)

    def video_ids(self) -> list[str]:
        return [
            row["video_id"]
            for row in self.connection.execute("SELECT video_id FROM videos")
        ]

    def videos(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM videos"))

    def snapshots(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM video_snapshots ORDER BY video_id, snapshot_date"
            )
        )

    def replace_themes(self, themes: Iterable[Theme]) -> None:
        calculated_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute("DELETE FROM theme_videos")
            self.connection.execute("DELETE FROM themes")
            for theme in themes:
                self.connection.execute(
                    """
                    INSERT INTO themes VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        theme.theme_id,
                        theme.theme_name,
                        theme.parent_category,
                        len(theme.video_ids),
                        theme.channel_count,
                        theme.median_views,
                        theme.median_views_per_day,
                        theme.median_view_subscriber_ratio,
                        theme.median_view_velocity,
                        theme.median_acceleration,
                        theme.median_engagement,
                        theme.correlation_score,
                        theme.consistency,
                        theme.opportunity_score,
                        theme.classification,
                        int(theme.high_confidence),
                        calculated_at,
                    ),
                )
                self.connection.executemany(
                    "INSERT INTO theme_videos VALUES (?, ?)",
                    [(theme.theme_id, video_id) for video_id in theme.video_ids],
                )

    def themes(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM themes ORDER BY opportunity_score DESC"
            )
        )

    def theme_memberships(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT tv.theme_id, v.*
                FROM theme_videos tv JOIN videos v USING(video_id)
                """
            )
        )
