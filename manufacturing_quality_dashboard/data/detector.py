from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

from config import CANONICAL_FIELDS


def normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def _score_match(column_name: str, candidates: Iterable[str]) -> int:
    normalized = normalize_name(column_name)
    best = 0
    for candidate in candidates:
        needle = normalize_name(candidate)
        if normalized == needle:
            best = max(best, 100)
        elif needle in normalized or normalized in needle:
            best = max(best, 70)
        else:
            col_tokens = set(normalized.split())
            candidate_tokens = set(needle.split())
            overlap = len(col_tokens & candidate_tokens)
            if overlap:
                score = int(40 * overlap / max(1, len(candidate_tokens)))
                best = max(best, score)
    return best


def detect_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    mapping: Dict[str, Optional[str]] = {field: None for field in CANONICAL_FIELDS}
    for field, aliases in CANONICAL_FIELDS.items():
        best_col = None
        best_score = 0
        for col in columns:
            score = _score_match(col, aliases)
            if score > best_score:
                best_score = score
                best_col = col
        mapping[field] = best_col if best_score >= 40 else None
    return mapping
