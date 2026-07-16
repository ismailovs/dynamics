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

CREATE TABLE IF NOT EXISTS discovered_videos (
    video_id TEXT PRIMARY KEY,
    discovery_category TEXT NOT NULL,
    discovery_query TEXT NOT NULL,
    first_discovered_at TIMESTAMP NOT NULL,
    last_discovered_at TIMESTAMP NOT NULL,
    details_status TEXT NOT NULL DEFAULT 'pending'
        CHECK(details_status IN ('pending', 'accepted', 'rejected', 'unavailable')),
    details_checked_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS search_cache (
    category TEXT NOT NULL,
    query TEXT NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    next_page_token TEXT,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (category, query)
);

CREATE TABLE IF NOT EXISTS api_quota_usage (
    usage_date DATE PRIMARY KEY,
    units_used INTEGER NOT NULL
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
CREATE INDEX IF NOT EXISTS idx_discovered_details_status
ON discovered_videos(details_status);
CREATE INDEX IF NOT EXISTS idx_snapshots_video_date
ON video_snapshots(video_id, snapshot_date);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
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

    def search_work(
        self,
        category: str,
        query: str,
        rolling_after: datetime,
        published_before: datetime,
    ) -> tuple[datetime, datetime, str, datetime] | None:
        row = self.connection.execute(
            "SELECT * FROM search_cache WHERE category=? AND query=?",
            (category, query),
        ).fetchone()
        if row is not None and row["next_page_token"] is not None:
            return (
                datetime.fromisoformat(row["window_start"]),
                datetime.fromisoformat(row["window_end"]),
                row["next_page_token"],
                datetime.fromisoformat(row["updated_at"]),
            )
        published_after = rolling_after
        if row is not None:
            published_after = max(
                published_after, datetime.fromisoformat(row["window_end"])
            )
        if published_after >= published_before:
            return None
        priority = (
            datetime.fromisoformat(row["updated_at"])
            if row is not None
            else datetime.min.replace(tzinfo=timezone.utc)
        )
        return published_after, published_before, "", priority

    def record_search_page(
        self,
        category: str,
        query: str,
        published_after: datetime,
        published_before: datetime,
        video_ids: Iterable[str],
        next_page_token: str,
        discovered_at: datetime | None = None,
    ) -> int:
        discovered_at = discovered_at or datetime.now(timezone.utc)
        unique_ids = set(video_ids)
        completed_at = None if next_page_token else discovered_at.isoformat()
        stored_token = next_page_token or None
        with self.connection:
            for video_id in unique_ids:
                self.connection.execute(
                    """
                    INSERT INTO discovered_videos (
                        video_id, discovery_category, discovery_query,
                        first_discovered_at, last_discovered_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(video_id) DO UPDATE SET
                        last_discovered_at=excluded.last_discovered_at
                    """,
                    (
                        video_id,
                        category,
                        query,
                        discovered_at.isoformat(),
                        discovered_at.isoformat(),
                    ),
                )
            self.connection.execute(
                """
                INSERT INTO search_cache VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(category, query) DO UPDATE SET
                    window_start=excluded.window_start,
                    window_end=excluded.window_end,
                    next_page_token=excluded.next_page_token,
                    completed_at=excluded.completed_at,
                    updated_at=excluded.updated_at
                """,
                (
                    category,
                    query,
                    published_after.isoformat(),
                    published_before.isoformat(),
                    stored_token,
                    completed_at,
                    discovered_at.isoformat(),
                ),
            )
        return len(unique_ids)

    def pending_discoveries(self) -> dict[str, str]:
        return {
            row["video_id"]: row["discovery_category"]
            for row in self.connection.execute(
                """
                SELECT video_id, discovery_category
                FROM discovered_videos
                WHERE details_status='pending'
                ORDER BY first_discovered_at, video_id
                """
            )
        }

    def mark_discovery_details(
        self,
        video_ids: Iterable[str],
        status: str,
        checked_at: datetime | None = None,
    ) -> int:
        if status not in {"accepted", "rejected", "unavailable"}:
            raise ValueError(f"Unsupported discovery status: {status}")
        checked_at = checked_at or datetime.now(timezone.utc)
        ids = list(set(video_ids))
        with self.connection:
            self.connection.executemany(
                """
                UPDATE discovered_videos
                SET details_status=?, details_checked_at=?
                WHERE video_id=?
                """,
                [(status, checked_at.isoformat(), video_id) for video_id in ids],
            )
        return len(ids)

    def discovered_videos(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM discovered_videos ORDER BY first_discovered_at, video_id"
            )
        )

    def record_api_request(
        self, resource: str, usage_date: date | None = None
    ) -> None:
        self.reserve_api_request(resource, usage_date)

    def reserve_api_request(
        self,
        resource: str,
        usage_date: date | None = None,
        daily_limit: int | None = None,
    ) -> bool:
        usage_date = usage_date or datetime.now(timezone.utc).date()
        units = 100 if resource == "search" else 1
        with self.connection:
            current = self.quota_units_used(usage_date)
            if daily_limit is not None and current + units > daily_limit:
                return False
            self.connection.execute(
                """
                INSERT INTO api_quota_usage VALUES (?, ?)
                ON CONFLICT(usage_date) DO UPDATE SET
                    units_used=units_used + excluded.units_used
                """,
                (usage_date.isoformat(), units),
            )
        return True

    def quota_units_used(self, usage_date: date | None = None) -> int:
        usage_date = usage_date or datetime.now(timezone.utc).date()
        row = self.connection.execute(
            "SELECT units_used FROM api_quota_usage WHERE usage_date=?",
            (usage_date.isoformat(),),
        ).fetchone()
        return int(row["units_used"]) if row is not None else 0

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
                        channel_id=excluded.channel_id,
                        channel_title=excluded.channel_title,
                        published_at=excluded.published_at,
                        duration_seconds=excluded.duration_seconds,
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
            saved = 0
            for video_id, (views, likes, comments) in statistics.items():
                if views < 0:
                    continue
                like_value = likes if likes >= 0 else None
                comment_value = comments if comments >= 0 else None
                updated = self.connection.execute(
                    """
                    UPDATE videos
                    SET view_count=?,
                        like_count=COALESCE(?, like_count),
                        comment_count=COALESCE(?, comment_count)
                    WHERE video_id=?
                    """,
                    (views, like_value, comment_value, video_id),
                )
                if updated.rowcount == 0:
                    continue
                self.connection.execute(
                    """
                    INSERT INTO video_snapshots
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(video_id, snapshot_date) DO UPDATE SET
                        view_count=excluded.view_count,
                        like_count=COALESCE(excluded.like_count, like_count),
                        comment_count=COALESCE(excluded.comment_count, comment_count)
                    """,
                    (
                        video_id,
                        snapshot_date.isoformat(),
                        views,
                        like_value,
                        comment_value,
                    ),
                )
                saved += 1
        return saved

    def video_ids(self) -> list[str]:
        return [
            row["video_id"]
            for row in self.connection.execute("SELECT video_id FROM videos")
        ]

    def videos(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM videos"))

    def videos_published_since(self, published_after: datetime) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM videos WHERE published_at >= ?",
                (published_after.isoformat(),),
            )
        )

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
