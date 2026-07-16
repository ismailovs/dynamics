"""Eligibility and duplicate filters for long-form English videos."""

from __future__ import annotations

import re
from collections import Counter

from .models import FilterResult, Video

ENGLISH_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "how",
    "in",
    "inside",
    "is",
    "of",
    "on",
    "the",
    "this",
    "to",
    "why",
    "with",
}
UNSUITABLE_PATTERNS = (
    re.compile(r"\bofficial\s+(music\s+)?video\b", re.IGNORECASE),
    re.compile(r"\blyric(s)?\s+video\b", re.IGNORECASE),
    re.compile(r"\b(movie\s+)?trailer\b", re.IGNORECASE),
    re.compile(r"\b(re-?upload(ed)?|mirror)\b", re.IGNORECASE),
)


def title_fingerprint(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.casefold()))


def is_probably_english(video: Video) -> bool:
    declared = video.language.casefold()
    if declared:
        return declared == "en" or declared.startswith("en-")
    sample = f"{video.title} {video.description[:300]}".casefold()
    letters = [character for character in sample if character.isalpha()]
    if not letters:
        return False
    ascii_ratio = sum(character.isascii() for character in letters) / len(letters)
    words = set(re.findall(r"[a-z]+", sample))
    return ascii_ratio >= 0.9 and bool(words & ENGLISH_WORDS)


def filter_videos(
    videos: list[Video],
    min_duration_seconds: int = 480,
    max_duration_seconds: int = 3600,
) -> FilterResult:
    accepted: list[Video] = []
    rejected: Counter[str] = Counter()
    seen_channel_titles: set[tuple[str, str]] = set()

    for video in videos:
        reason = ""
        if not min_duration_seconds <= video.duration_seconds <= max_duration_seconds:
            reason = "duration"
        elif video.live_broadcast_content != "none":
            reason = "livestream"
        elif min(video.view_count, video.like_count, video.comment_count) < 0:
            reason = "missing_statistics"
        elif video.category == "10":
            reason = "music"
        elif any(pattern.search(video.title) for pattern in UNSUITABLE_PATTERNS):
            reason = "unsuitable_title"
        elif not is_probably_english(video):
            reason = "non_english"
        else:
            duplicate_key = (video.channel_id, title_fingerprint(video.title))
            if duplicate_key in seen_channel_titles:
                reason = "duplicate_channel_title"
            else:
                seen_channel_titles.add(duplicate_key)

        if reason:
            rejected[reason] += 1
        else:
            accepted.append(video)

    return FilterResult(accepted=accepted, rejected=dict(rejected))
