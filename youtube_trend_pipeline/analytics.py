"""Clustering, growth metrics, and opportunity scoring."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import median
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from .models import Theme


def build_themes(
    video_rows: list[Any],
    snapshot_rows: list[Any],
    target_clusters: int = 200,
    min_theme_videos: int = 5,
    random_state: int = 42,
    now: datetime | None = None,
) -> list[Theme]:
    if len(video_rows) < min_theme_videos:
        return []
    now = now or datetime.now(timezone.utc)
    texts = [_cluster_text(row) for row in video_rows]
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1 if len(texts) < 100 else 2,
        max_df=0.95,
        max_features=20_000,
        sublinear_tf=True,
    )
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError as error:
        if "empty vocabulary" in str(error):
            return []
        raise
    cluster_count = max(1, min(target_clusters, len(video_rows) // min_theme_videos))
    model = KMeans(
        n_clusters=cluster_count,
        random_state=random_state,
        n_init=10,
    )
    labels = model.fit_predict(matrix)
    terms = vectorizer.get_feature_names_out()
    snapshots = _snapshot_map(snapshot_rows)

    themes: list[Theme] = []
    for label in range(cluster_count):
        indexes = np.flatnonzero(labels == label)
        if len(indexes) < min_theme_videos:
            continue
        top_indices = model.cluster_centers_[label].argsort()[::-1][:8]
        top_terms = [terms[index] for index in top_indices]
        rows = [video_rows[index] for index in indexes]
        name = _theme_name(top_terms)
        consistency = _keyword_consistency(texts, indexes, top_terms[:5])
        theme = _theme_metrics(
            theme_id=len(themes) + 1,
            name=name,
            rows=rows,
            snapshots=snapshots,
            consistency=consistency,
            now=now,
        )
        themes.append(theme)

    _score_themes(themes, video_rows)
    return sorted(themes, key=lambda theme: theme.opportunity_score, reverse=True)


def _cluster_text(row: Any) -> str:
    try:
        tags = " ".join(json.loads(row["tags"] or "[]"))
    except (TypeError, json.JSONDecodeError):
        tags = ""
    return " ".join(
        filter(
            None,
            (
                row["title"],
                (row["description"] or "")[:500],
                tags,
                row["discovery_category"] or "",
            ),
        )
    )


def _snapshot_map(rows: list[Any]) -> dict[str, list[tuple[float, float]]]:
    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in rows:
        grouped[row["video_id"]].append((row["snapshot_date"], row["view_count"]))
    result: dict[str, list[tuple[float, float]]] = {}
    for video_id, values in grouped.items():
        values.sort()
        first_date = datetime.fromisoformat(values[0][0]).date()
        result[video_id] = [
            ((datetime.fromisoformat(day).date() - first_date).days, views)
            for day, views in values
        ]
    return result


def _growth(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    if len(points) < 2:
        return 0.0, 0.0, 0.0
    days = np.array([point[0] for point in points], dtype=float)
    views = np.array([point[1] for point in points], dtype=float)
    intervals = np.diff(days)
    valid = intervals > 0
    daily = np.diff(views)[valid] / intervals[valid]
    if not len(daily):
        return 0.0, 0.0, 0.0
    velocity = float(np.median(daily))
    acceleration = (
        float(np.polyfit(days[1:][valid], daily, 1)[0]) if len(daily) >= 2 else 0.0
    )
    correlation = (
        float(np.corrcoef(days, views)[0, 1])
        if len(points) >= 3 and np.std(views) > 0
        else 0.0
    )
    return velocity, acceleration, correlation


def _theme_metrics(
    theme_id: int,
    name: str,
    rows: list[Any],
    snapshots: dict[str, list[tuple[float, float]]],
    consistency: float,
    now: datetime,
) -> Theme:
    views = [float(row["view_count"]) for row in rows]
    views_per_day: list[float] = []
    subscriber_ratios: list[float] = []
    engagements: list[float] = []
    velocities: list[float] = []
    accelerations: list[float] = []
    correlations: list[float] = []
    categories: Counter[str] = Counter()

    for row in rows:
        published_at = datetime.fromisoformat(row["published_at"])
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        age_hours = max((now - published_at).total_seconds() / 3600, 1)
        views_per_day.append(row["view_count"] / age_hours * 24)
        if row["subscriber_count"] >= 0:
            subscriber_ratios.append(
                row["view_count"] / max(row["subscriber_count"], 1)
            )
        engagements.append(
            (row["like_count"] + row["comment_count"] * 2)
            / max(row["view_count"], 1)
        )
        velocity, acceleration, correlation = _growth(
            snapshots.get(row["video_id"], [])
        )
        velocities.append(velocity)
        accelerations.append(acceleration)
        correlations.append(correlation)
        categories[row["discovery_category"] or "Uncategorized"] += 1

    return Theme(
        theme_id=theme_id,
        theme_name=name,
        parent_category=categories.most_common(1)[0][0],
        video_ids=[row["video_id"] for row in rows],
        channel_count=len({row["channel_id"] for row in rows}),
        median_views=median(views),
        median_views_per_day=median(views_per_day),
        median_view_subscriber_ratio=median(subscriber_ratios)
        if subscriber_ratios
        else None,
        median_view_velocity=median(velocities),
        median_acceleration=median(accelerations),
        median_engagement=median(engagements),
        correlation_score=median(correlations),
        consistency=consistency,
    )


def _keyword_consistency(
    texts: list[str], indexes: np.ndarray[Any, Any], terms: list[str]
) -> float:
    matches = 0
    for index in indexes:
        text = texts[int(index)].casefold()
        if any(term.casefold() in text for term in terms):
            matches += 1
    return matches / len(indexes)


def _theme_name(terms: list[str]) -> str:
    selected: list[str] = []
    used_words: set[str] = set()
    for term in terms:
        words = set(term.split())
        if words - used_words:
            selected.append(term)
            used_words.update(words)
        if len(selected) == 3:
            break
    return " / ".join(selected).title()


def _percentile_ranks(values: list[float | None]) -> list[float | None]:
    known = [index for index, value in enumerate(values) if value is not None]
    result: list[float | None] = [None] * len(values)
    if len(known) == 1:
        result[known[0]] = 50.0
        return result
    if not known:
        return result
    order = sorted(known, key=lambda index: values[index])  # type: ignore[arg-type]
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        rank = ((position + end) / 2) / (len(order) - 1) * 100
        for index in order[position : end + 1]:
            result[index] = rank
        position = end + 1
    return result


def _score_themes(themes: list[Theme], video_rows: list[Any]) -> None:
    if not themes:
        return
    metrics = (
        ("median_views_per_day", 0.25),
        ("median_view_subscriber_ratio", 0.20),
        ("median_view_velocity", 0.15),
        ("median_acceleration", 0.10),
        ("median_engagement", 0.10),
        ("channel_count", 0.10),
        ("correlation_score", 0.05),
        ("consistency", 0.05),
    )
    normalized = {
        name: _percentile_ranks([getattr(theme, name) for theme in themes])
        for name, _ in metrics
    }
    views_by_id = {row["video_id"]: row["view_count"] for row in video_rows}

    for index, theme in enumerate(themes):
        components = [
            (normalized[name][index], weight) for name, weight in metrics
        ]
        available_weight = sum(
            weight for value, weight in components if value is not None
        )
        theme.opportunity_score = round(
            sum(
                value * weight
                for value, weight in components
                if value is not None
            )
            / available_weight,
            1,
        )
        total_views = sum(views_by_id[video_id] for video_id in theme.video_ids)
        dominant_share = (
            max(views_by_id[video_id] for video_id in theme.video_ids)
            / max(total_views, 1)
        )
        theme.high_confidence = (
            len(theme.video_ids) >= 5
            and theme.channel_count >= 3
            and theme.median_view_velocity > 0
            and dominant_share <= 0.5
            and theme.consistency >= 0.7
        )
        theme.classification = _classification(theme.opportunity_score)


def _classification(score: float) -> str:
    if score >= 85:
        return "Breakout theme"
    if score >= 70:
        return "Strong opportunity"
    if score >= 55:
        return "Promising"
    if score >= 40:
        return "Monitor"
    return "Weak or saturated"
