"""Shared data structures for the trend pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Video:
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: datetime
    duration_seconds: int
    view_count: int
    like_count: int
    comment_count: int
    subscriber_count: int
    tags: list[str] = field(default_factory=list)
    language: str = ""
    thumbnail_url: str = ""
    category: str = ""
    discovery_category: str = ""
    live_broadcast_content: str = "none"

    @property
    def cluster_text(self) -> str:
        excerpt = self.description[:500]
        return " ".join(
            part
            for part in (
                self.title,
                excerpt,
                " ".join(self.tags),
                self.discovery_category,
            )
            if part
        )


@dataclass(slots=True)
class FilterResult:
    accepted: list[Video]
    rejected: dict[str, int]


@dataclass(slots=True)
class Theme:
    theme_id: int
    theme_name: str
    parent_category: str
    video_ids: list[str]
    channel_count: int
    median_views: float
    median_views_per_day: float
    median_view_subscriber_ratio: float
    median_view_velocity: float
    median_acceleration: float
    median_engagement: float
    correlation_score: float
    consistency: float
    opportunity_score: float = 0.0
    classification: str = ""
    high_confidence: bool = False
