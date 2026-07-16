"""Small dependency-free client for the YouTube Data API v3."""

from __future__ import annotations

import json
import time
from collections import deque
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from .models import Video
from .queries import iter_queries

API_ROOT = "https://www.googleapis.com/youtube/v3"


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_duration(value: str) -> int:
    """Parse the date-free subset of ISO-8601 durations returned by YouTube."""
    if not value.startswith("PT"):
        raise ValueError(f"Unsupported duration: {value}")
    value = value[2:]
    total = 0
    number = ""
    multipliers = {"H": 3600, "M": 60, "S": 1}
    for character in value:
        if character.isdigit():
            number += character
        elif character in multipliers and number:
            total += int(number) * multipliers[character]
            number = ""
        else:
            raise ValueError(f"Unsupported duration: PT{value}")
    return total


class YouTubeClient:
    def __init__(
        self,
        api_key: str,
        request_json: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_429_retries: int = 5,
    ) -> None:
        if not api_key and request_json is None:
            raise ValueError("YOUTUBE_API_KEY is required for live collection")
        self.api_key = api_key
        self._transport = request_json or self._http_request
        self._sleep = sleep
        self._max_429_retries = max_429_retries

    def _http_request(self, resource: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urlencode({**params, "key": self.api_key})
        with urlopen(f"{API_ROOT}/{resource}?{query}", timeout=30) as response:
            return json.load(response)

    def _request_json(
        self, resource: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                return self._transport(resource, params)
            except HTTPError as error:
                if error.code != 429 or attempt >= self._max_429_retries:
                    raise
                self._sleep(float(2**attempt))
                attempt += 1

    def search_page(
        self,
        query: str,
        published_after: datetime,
        published_before: datetime,
        page_token: str = "",
    ) -> tuple[list[str], str]:
        """Use search.list only to return up to 50 unique video IDs."""
        params: dict[str, Any] = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "date",
            "maxResults": 50,
            "publishedAfter": published_after.isoformat().replace("+00:00", "Z"),
            "publishedBefore": published_before.isoformat().replace("+00:00", "Z"),
        }
        if page_token:
            params["pageToken"] = page_token
        payload = self._request_json("search", params)
        video_ids = list(
            dict.fromkeys(
                video_id
                for item in payload.get("items", [])
                if (video_id := item.get("id", {}).get("videoId"))
            )
        )
        return video_ids, payload.get("nextPageToken", "")

    def discover(
        self,
        published_after: datetime,
        published_before: datetime,
        max_search_requests: int,
    ) -> dict[str, str]:
        """Return unique video IDs mapped to their first discovery category."""
        discovered: dict[str, str] = {}
        request_count = 0
        pages = deque((category, query, "") for category, query in iter_queries())
        while pages and request_count < max_search_requests:
            category, query, page_token = pages.popleft()
            video_ids, next_page = self.search_page(
                query, published_after, published_before, page_token
            )
            request_count += 1
            for video_id in video_ids:
                discovered.setdefault(video_id, category)
            if next_page:
                pages.append((category, query, next_page))
        return discovered

    def fetch_videos(self, discovered: dict[str, str]) -> list[Video]:
        videos: list[Video] = []
        for video_ids in _batches(discovered, 50):
            payload = self._request_json(
                "videos",
                {
                    "part": "snippet,contentDetails,statistics",
                    "id": ",".join(video_ids),
                    "maxResults": 50,
                },
            )
            channel_ids = {
                item.get("snippet", {}).get("channelId", "")
                for item in payload.get("items", [])
            }
            subscribers = self._fetch_subscribers(channel_ids)
            for item in payload.get("items", []):
                video = self._to_video(item, discovered, subscribers)
                if video is not None:
                    videos.append(video)
        return videos

    def refresh_statistics(self, video_ids: Iterable[str]) -> dict[str, tuple[int, int, int]]:
        result: dict[str, tuple[int, int, int]] = {}
        for batch in _batches(video_ids, 50):
            payload = self._request_json(
                "videos",
                {"part": "statistics", "id": ",".join(batch), "maxResults": 50},
            )
            for item in payload.get("items", []):
                stats = item.get("statistics", {})
                result[item["id"]] = (
                    int(stats.get("viewCount", -1)),
                    int(stats.get("likeCount", -1)),
                    int(stats.get("commentCount", -1)),
                )
        return result

    def _fetch_subscribers(self, channel_ids: set[str]) -> dict[str, int]:
        result: dict[str, int] = {}
        for batch in _batches(filter(None, channel_ids), 50):
            payload = self._request_json(
                "channels",
                {"part": "statistics", "id": ",".join(batch), "maxResults": 50},
            )
            for item in payload.get("items", []):
                statistics = item.get("statistics", {})
                result[item["id"]] = (
                    -1
                    if statistics.get("hiddenSubscriberCount")
                    else int(statistics.get("subscriberCount", -1))
                )
        return result

    @staticmethod
    def _to_video(
        item: dict[str, Any],
        discovered: dict[str, str],
        subscribers: dict[str, int],
    ) -> Video | None:
        try:
            snippet = item["snippet"]
            details = item["contentDetails"]
            statistics = item["statistics"]
            thumbnails = snippet.get("thumbnails", {})
            thumbnail = thumbnails.get("high") or thumbnails.get("default") or {}
            channel_id = snippet["channelId"]
            language = (
                snippet.get("defaultAudioLanguage")
                or snippet.get("defaultLanguage")
                or ""
            )
            return Video(
                video_id=item["id"],
                title=snippet["title"],
                description=snippet.get("description", ""),
                channel_id=channel_id,
                channel_title=snippet.get("channelTitle", ""),
                published_at=parse_timestamp(snippet["publishedAt"]),
                duration_seconds=parse_duration(details["duration"]),
                view_count=int(statistics.get("viewCount", -1)),
                like_count=int(statistics.get("likeCount", -1)),
                comment_count=int(statistics.get("commentCount", -1)),
                subscriber_count=subscribers.get(channel_id, -1),
                tags=snippet.get("tags", []),
                language=language,
                thumbnail_url=thumbnail.get("url", ""),
                category=snippet.get("categoryId", ""),
                discovery_category=discovered.get(item["id"], ""),
                live_broadcast_content=snippet.get("liveBroadcastContent", "none"),
            )
        except (KeyError, TypeError, ValueError):
            return None


def _batches(values: Iterable[str], size: int) -> Iterable[list[str]]:
    batch: list[str] = []
    for value in values:
        batch.append(value)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch
