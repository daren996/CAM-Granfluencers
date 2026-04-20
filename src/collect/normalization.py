from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any


HASHTAG_PATTERN = re.compile(r"#([A-Za-z0-9_]+)")

MEDIA_TYPE_MAP = {
    1: "image",
    2: "video",
    8: "carousel",
}


def timestamp_to_iso8601(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError):
        return None


def extract_hashtags(text: str | None) -> list[str]:
    if not text:
        return []
    seen: set[str] = set()
    hashtags: list[str] = []
    for match in HASHTAG_PATTERN.findall(text):
        lowered = match.lower()
        if lowered not in seen:
            seen.add(lowered)
            hashtags.append(lowered)
    return hashtags


def media_type_name(value: Any) -> str:
    try:
        return MEDIA_TYPE_MAP[int(value)]
    except (KeyError, TypeError, ValueError):
        return "unknown"


def first_image_url(item: dict[str, Any]) -> str | None:
    image_versions = item.get("image_versions2", {}) or {}
    candidates = image_versions.get("candidates", []) or []
    if candidates:
        return candidates[0].get("url")
    return item.get("display_url")


def video_urls(item: dict[str, Any]) -> list[str]:
    versions = item.get("video_versions", []) or []
    return [version.get("url") for version in versions if version.get("url")]
