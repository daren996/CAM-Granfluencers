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


def primary_video_url(item: dict[str, Any]) -> str | None:
    versions = item.get("video_versions", []) or []
    for version in versions:
        url = version.get("url")
        if url:
            return url
    return None


def media_assets(item: dict[str, Any]) -> list[dict[str, Any]]:
    entries = item.get("carousel_media") or [item]
    assets: list[dict[str, Any]] = []

    for position, entry in enumerate(entries, start=1):
        media_entry = entry or {}
        media_type = media_type_name(media_entry.get("media_type", item.get("media_type")))
        image_url = first_image_url(media_entry)
        video_url = primary_video_url(media_entry)

        if media_type == "video" and video_url:
            asset = {
                "position": position,
                "media_type": "video",
                "url": video_url,
            }
            if image_url:
                asset["thumbnail_url"] = image_url
            assets.append(asset)
            continue

        if image_url:
            assets.append(
                {
                    "position": position,
                    "media_type": "image",
                    "url": image_url,
                    "thumbnail_url": image_url,
                }
            )
            continue

        if video_url:
            assets.append(
                {
                    "position": position,
                    "media_type": "video",
                    "url": video_url,
                }
            )

    return assets


def image_urls(item: dict[str, Any]) -> list[str]:
    return [asset["url"] for asset in media_assets(item) if asset.get("media_type") == "image"]


def video_urls(item: dict[str, Any]) -> list[str]:
    return [asset["url"] for asset in media_assets(item) if asset.get("media_type") == "video"]
