"""End-to-end orchestration for collection, snapshots, analysis, and export."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .analytics import build_themes
from .config import Settings
from .database import Database
from .filtering import filter_videos, title_fingerprint
from .models import FilterResult, Video
from .youtube import YouTubeClient


class TrendPipeline:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def collect(
        self, client: YouTubeClient, now: datetime | None = None
    ) -> FilterResult:
        now = now or datetime.now(timezone.utc)
        published_after = now - timedelta(days=self.settings.window_days)
        active_count = len(self.database.videos_published_since(published_after))
        discovered = client.discover(
            published_after=published_after,
            published_before=now,
            max_search_requests=self._search_request_budget(active_count),
        )
        return self.ingest(client.fetch_videos(discovered), collected_at=now)

    def ingest(
        self, videos: list[Video], collected_at: datetime | None = None
    ) -> FilterResult:
        result = filter_videos(
            videos,
            min_duration_seconds=self.settings.min_duration_seconds,
            max_duration_seconds=self.settings.max_duration_seconds,
        )
        existing = {
            (row["channel_id"], row["title_fingerprint"]): row["video_id"]
            for row in self.database.videos()
        }
        accepted: list[Video] = []
        duplicate_count = 0
        for video in result.accepted:
            key = (video.channel_id, title_fingerprint(video.title))
            if key in existing and existing[key] != video.video_id:
                duplicate_count += 1
            else:
                accepted.append(video)
        if duplicate_count:
            result.rejected["duplicate_channel_title"] = (
                result.rejected.get("duplicate_channel_title", 0) + duplicate_count
            )
        result.accepted = accepted
        self.database.upsert_videos(accepted, collected_at)
        return result

    def refresh(
        self, client: YouTubeClient, now: datetime | None = None
    ) -> int:
        now = now or datetime.now(timezone.utc)
        active_rows = self.database.videos_published_since(
            now - timedelta(days=self.settings.window_days)
        )
        statistics = client.refresh_statistics(
            row["video_id"] for row in active_rows
        )
        return self.database.snapshot(statistics)

    def snapshot_current(self) -> int:
        return self.database.snapshot()

    def analyze(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        active_videos = self.database.videos_published_since(
            now - timedelta(days=self.settings.window_days)
        )
        themes = build_themes(
            active_videos,
            self.database.snapshots(),
            target_clusters=self.settings.target_clusters,
            min_theme_videos=self.settings.min_theme_videos,
            random_state=self.settings.random_state,
            now=now,
        )
        self.database.replace_themes(themes)
        return len(themes)

    def _search_request_budget(self, active_video_count: int) -> int:
        """Reserve quota for details and one refresh of every active video."""
        existing_refresh_units = (active_video_count + 49) // 50
        remaining = max(self.settings.daily_quota_units - existing_refresh_units, 0)
        # Each search costs 100 units and can trigger one videos.list, one
        # channels.list, and one later refresh batch at one unit each.
        quota_limited_requests = remaining // 103
        return min(self.settings.max_search_requests, quota_limited_requests)
