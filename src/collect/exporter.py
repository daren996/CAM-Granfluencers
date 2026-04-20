from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .storage import utc_now_iso, write_json


DASHBOARD_EXPORT_FILES = {
    "site_summary": "site-summary.json",
    "accounts": "accounts.json",
    "posts": "posts.json",
    "hashtags": "hashtags.json",
    "engagement_timeseries": "engagement-timeseries.json",
}


def export_dashboard_data(
    input_path: str | Path, output_dir: str | Path = "data/dashboard"
) -> dict[str, str]:
    bundles = _load_bundles(Path(input_path))
    output_path = Path(output_dir)
    accounts = _build_accounts(bundles)
    posts = _build_posts(bundles)
    comments = _build_comments(bundles)
    hashtags = _build_hashtags(posts)
    timeseries = _build_timeseries(posts)
    site_summary = _build_site_summary(accounts, posts, comments, bundles)

    payloads = {
        "site_summary": site_summary,
        "accounts": accounts,
        "posts": posts,
        "hashtags": hashtags,
        "engagement_timeseries": timeseries,
    }
    written = {
        key: str(write_json(output_path / DASHBOARD_EXPORT_FILES[key], payload))
        for key, payload in payloads.items()
    }
    return written


def sync_docs_data(
    source_dir: str | Path = "data/dashboard", docs_dir: str | Path = "docs/data"
) -> dict[str, str]:
    source_path = Path(source_dir)
    docs_path = Path(docs_dir)
    written: dict[str, str] = {}

    for key, filename in DASHBOARD_EXPORT_FILES.items():
        source_file = source_path / filename
        if not source_file.exists():
            raise FileNotFoundError(f"Missing dashboard data file: {source_file}")
        payload = json.loads(source_file.read_text(encoding="utf-8"))
        written[key] = str(write_json(docs_path / filename, payload))

    return written


def _load_bundles(path: Path) -> list[dict[str, Any]]:
    if path.is_file():
        return [_load_json(path)]
    bundle_paths = sorted(path.rglob("bundle.json"))
    return [_load_json(bundle_path) for bundle_path in bundle_paths]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_accounts(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    for bundle in bundles:
        profile = bundle.get("profile") or {}
        if not profile:
            continue
        accounts.append(
            {
                "platform": profile.get("platform"),
                "account_id": profile.get("account_id"),
                "username": profile.get("username"),
                "full_name": profile.get("full_name"),
                "biography": profile.get("biography"),
                "external_url": profile.get("external_url"),
                "profile_pic_url": profile.get("profile_pic_url"),
                "is_verified": profile.get("is_verified"),
                "is_private": profile.get("is_private"),
                "followers": profile.get("followers_count"),
                "following": profile.get("following_count"),
                "posts_count": profile.get("posts_count"),
                "reels_count": profile.get("reels_count"),
                "collected_at": bundle.get("collected_at"),
            }
        )
    return accounts


def _build_posts(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for bundle in bundles:
        for post in bundle.get("posts", []):
            posts.append(
                {
                    "platform": post.get("platform"),
                    "post_id": post.get("post_id"),
                    "code": post.get("code"),
                    "url": post.get("url"),
                    "account_id": post.get("author", {}).get("account_id"),
                    "username": post.get("author", {}).get("username"),
                    "caption": post.get("caption"),
                    "hashtags": post.get("hashtags", []),
                    "media_type": post.get("media_type"),
                    "likes": post.get("metrics", {}).get("likes"),
                    "comments": post.get("metrics", {}).get("comments"),
                    "taken_at": post.get("taken_at"),
                    "thumbnail_url": post.get("thumbnail_url"),
                }
            )
    posts.sort(key=lambda item: item.get("taken_at") or "", reverse=True)
    return posts


def _build_comments(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for bundle in bundles:
        comments.extend(bundle.get("comments", []))
        comments.extend(bundle.get("replies", []))
    return comments


def _build_hashtags(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hashtag_counter: Counter[str] = Counter()
    for post in posts:
        hashtag_counter.update(post.get("hashtags") or [])
    return [
        {"hashtag": hashtag, "post_count": count}
        for hashtag, count in hashtag_counter.most_common()
    ]


def _build_timeseries(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"date": None, "posts": 0, "likes": 0, "comments": 0}
    )
    for post in posts:
        taken_at = post.get("taken_at")
        if not taken_at:
            continue
        date = taken_at[:10]
        bucket = buckets[date]
        bucket["date"] = date
        bucket["posts"] += 1
        bucket["likes"] += int(post.get("likes") or 0)
        bucket["comments"] += int(post.get("comments") or 0)
    return [buckets[key] for key in sorted(buckets)]


def _build_site_summary(
    accounts: list[dict[str, Any]],
    posts: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> dict[str, Any]:
    post_dates = [post["taken_at"] for post in posts if post.get("taken_at")]
    collected_at_values = [
        bundle.get("collected_at") for bundle in bundles if bundle.get("collected_at")
    ]
    return {
        "updated_at": max(collected_at_values) if collected_at_values else utc_now_iso(),
        "project_status": "ready_with_data" if posts else "waiting_for_data",
        "counts": {
            "accounts": len(accounts),
            "posts": len(posts),
            "comments": len(comments),
        },
        "date_range": {
            "start": min(post_dates) if post_dates else None,
            "end": max(post_dates) if post_dates else None,
        },
    }
