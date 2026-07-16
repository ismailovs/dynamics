"""End-to-end orchestration for collection, snapshots, analysis, and export."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone

from .analytics import build_themes
from .config import Settings
from .database import Database
from .filtering import filter_videos, title_fingerprint
from .models import FilterResult, Video
from .queries import iter_queries
from .youtube import YouTubeClient


class TrendPipeline:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def collect(
        self, client: YouTubeClient, now: datetime | None = None
    ) -> FilterResult:
        now = now or datetime.now(timezone.utc)
        self._attach_usage_recorder(client, now)
        published_after = now - timedelta(days=self.settings.window_days)
        active_count = len(self.database.videos_published_since(published_after))
        pending_count = len(self.database.pending_discoveries())
        self._discover_and_cache(
            client,
            published_after,
            now,
            self._search_request_budget(
                active_count,
                pending_count,
                self.database.quota_units_used(now.date()),
            ),
        )
        pending = self.database.pending_discoveries()
        if not pending:
            return FilterResult(accepted=[], rejected={})
        videos = client.fetch_videos(pending)
        result = self.ingest(videos, collected_at=now)
        requested_ids = set(pending)
        fetched_ids = {video.video_id for video in videos}
        accepted_ids = {video.video_id for video in result.accepted}
        self.database.mark_discovery_details(accepted_ids, "accepted", now)
        self.database.mark_discovery_details(
            fetched_ids - accepted_ids, "rejected", now
        )
        unavailable_ids = requested_ids - fetched_ids
        self.database.mark_discovery_details(unavailable_ids, "unavailable", now)
        if unavailable_ids:
            result.rejected["unavailable_metadata"] = len(unavailable_ids)
        return result

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
        self._attach_usage_recorder(client, now)
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

    def _discover_and_cache(
        self,
        client: YouTubeClient,
        published_after: datetime,
        published_before: datetime,
        request_budget: int,
    ) -> int:
        queued_pages = []
        for matrix_index, (category, query) in enumerate(iter_queries()):
            work = self.database.search_work(
                category, query, published_after, published_before
            )
            if work is not None:
                window_start, window_end, page_token, priority = work
                queued_pages.append(
                    (
                        priority,
                        matrix_index,
                        category,
                        query,
                        window_start,
                        window_end,
                        page_token,
                    )
                )
        queued_pages.sort(key=lambda page: (page[0], page[1]))
        pages = deque(queued_pages)

        request_count = 0
        while pages and request_count < request_budget:
            (
                _priority,
                matrix_index,
                category,
                query,
                window_start,
                window_end,
                page_token,
            ) = pages.popleft()
            video_ids, next_page_token = client.search_page(
                query, window_start, window_end, page_token
            )
            self.database.record_search_page(
                category,
                query,
                window_start,
                window_end,
                video_ids,
                next_page_token,
                discovered_at=published_before,
            )
            request_count += 1
            if next_page_token:
                pages.append(
                    (
                        published_before,
                        matrix_index,
                        category,
                        query,
                        window_start,
                        window_end,
                        next_page_token,
                    )
                )
        return request_count

    def _search_request_budget(
        self,
        active_video_count: int,
        pending_video_count: int = 0,
        quota_units_used: int = 0,
    ) -> int:
        """Reserve quota for details and one refresh of every active video."""
        existing_refresh_units = (active_video_count + 49) // 50
        pending_batches = (pending_video_count + 49) // 50
        remaining = max(
            self.settings.daily_quota_units
            - quota_units_used
            - existing_refresh_units
            - pending_batches * 3,
            0,
        )
        # Each search costs 100 units and can trigger one videos.list, one
        # channels.list, and one later refresh batch at one unit each.
        quota_limited_requests = remaining // 103
        return min(self.settings.max_search_requests, quota_limited_requests)

    def _attach_usage_recorder(
        self, client: YouTubeClient, now: datetime
    ) -> None:
        if hasattr(client, "set_usage_recorder"):
            client.set_usage_recorder(
                lambda resource: self.database.record_api_request(
                    resource, now.date()
                )
            )
