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
    collected = load_collected_data(Path(input_path))
    output_path = Path(output_dir)
    accounts = _build_accounts(collected)
    posts = _build_posts(collected)
    comments = _build_comments(collected)
    hashtags = _build_hashtags(posts)
    timeseries = _build_timeseries(posts)
    site_summary = _build_site_summary(accounts, posts, comments, collected)

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


def load_collected_data(path: Path) -> dict[str, list[dict[str, Any]]]:
    legacy_bundles: list[dict[str, Any]] = []
    account_docs: list[dict[str, Any]] = []
    item_docs: list[dict[str, Any]] = []

    if path.is_file():
        payload = _load_json(path)
        if path.name == "bundle.json":
            legacy_bundles.append(payload)
        elif path.name == "account.json":
            account_docs.append(payload)
            item_docs.extend(_load_neighbor_item_docs(path.parent))
        elif path.name == "item.json":
            item_docs.append(payload)
        else:
            raise ValueError(f"Unsupported collection input file: {path}")
        return {
            "legacy_bundles": legacy_bundles,
            "account_docs": account_docs,
            "item_docs": item_docs,
        }

    legacy_bundles = [_load_json(bundle_path) for bundle_path in sorted(path.rglob("bundle.json"))]
    account_docs = [_load_json(account_path) for account_path in sorted(path.rglob("account.json"))]
    item_docs = [_load_json(item_path) for item_path in sorted(path.rglob("item.json"))]
    return {
        "legacy_bundles": legacy_bundles,
        "account_docs": account_docs,
        "item_docs": item_docs,
    }


def _load_neighbor_item_docs(account_dir: Path) -> list[dict[str, Any]]:
    return [_load_json(item_path) for item_path in sorted(account_dir.rglob("item.json"))]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_accounts(collected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    accounts_by_key: dict[tuple[str | None, str | None, str | None], dict[str, Any]] = {}

    for bundle in collected.get("legacy_bundles", []):
        profile = bundle.get("profile") or {}
        if not profile:
            continue
        row = {
            "platform": profile.get("platform"),
            "account_id": profile.get("account_id"),
            "username": profile.get("username"),
            "full_name": profile.get("full_name"),
            "biography": profile.get("biography"),
            "external_url": profile.get("external_url"),
            "profile_pic_url": profile.get("profile_pic_url"),
            "profile_pic_local_path": profile.get("profile_pic_local_path"),
            "is_verified": profile.get("is_verified"),
            "is_private": profile.get("is_private"),
            "followers": profile.get("followers_count"),
            "following": profile.get("following_count"),
            "posts_count": profile.get("posts_count"),
            "reels_count": profile.get("reels_count"),
            "stored_items": len(bundle.get("posts", [])),
            "stored_posts": len(bundle.get("posts", [])),
            "stored_reels": 0,
            "stored_likes": sum(
                int((post.get("metrics") or {}).get("likes") or 0)
                for post in bundle.get("posts", [])
            ),
            "stored_comments": sum(
                int((post.get("metrics") or {}).get("comments") or 0)
                for post in bundle.get("posts", [])
            ),
            "collected_at": bundle.get("collected_at"),
        }
        _keep_latest(
            accounts_by_key,
            _account_key(row),
            row,
            row.get("collected_at"),
        )

    for account_doc in collected.get("account_docs", []):
        profile = account_doc.get("profile") or {}
        if not profile:
            continue
        metrics = account_doc.get("metrics") or {}
        row = {
            "platform": profile.get("platform"),
            "account_id": profile.get("account_id"),
            "username": profile.get("username"),
            "full_name": profile.get("full_name"),
            "biography": profile.get("biography"),
            "external_url": profile.get("external_url"),
            "profile_pic_url": profile.get("profile_pic_url"),
            "profile_pic_local_path": profile.get("profile_pic_local_path"),
            "is_verified": profile.get("is_verified"),
            "is_private": profile.get("is_private"),
            "followers": profile.get("followers_count"),
            "following": profile.get("following_count"),
            "posts_count": profile.get("posts_count"),
            "reels_count": profile.get("reels_count"),
            "stored_items": metrics.get("stored_items"),
            "stored_posts": metrics.get("stored_posts"),
            "stored_reels": metrics.get("stored_reels"),
            "stored_likes": metrics.get("stored_likes"),
            "stored_comments": metrics.get("stored_comments"),
            "collected_at": account_doc.get("extracted_at") or account_doc.get("collected_at"),
        }
        _keep_latest(
            accounts_by_key,
            _account_key(row),
            row,
            row.get("collected_at"),
        )

    accounts = list(accounts_by_key.values())
    accounts.sort(key=lambda item: (item.get("username") or "", item.get("account_id") or ""))
    return accounts


def _build_posts(collected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    posts_by_key: dict[tuple[str | None, str | None, str | None], dict[str, Any]] = {}

    for bundle in collected.get("legacy_bundles", []):
        extracted_at = bundle.get("collected_at")
        for post in bundle.get("posts", []):
            row = _post_row(post, extracted_at=extracted_at)
            _keep_latest(posts_by_key, _post_key(row), row, extracted_at)

    for item_doc in collected.get("item_docs", []):
        post = item_doc.get("post") or {}
        if not post:
            continue
        extracted_at = item_doc.get("extracted_at") or item_doc.get("collected_at")
        row = _post_row(post, extracted_at=extracted_at)
        _keep_latest(posts_by_key, _post_key(row), row, extracted_at)

    posts = list(posts_by_key.values())
    posts.sort(
        key=lambda item: (
            item.get("taken_at") or "",
            item.get("collected_at") or "",
        ),
        reverse=True,
    )
    return posts


def _post_row(post: dict[str, Any], *, extracted_at: str | None) -> dict[str, Any]:
    return {
        "platform": post.get("platform"),
        "post_id": post.get("post_id"),
        "code": post.get("code"),
        "url": post.get("url"),
        "item_type": post.get("item_type") or "post",
        "account_id": post.get("author", {}).get("account_id"),
        "username": post.get("author", {}).get("username"),
        "caption": post.get("caption"),
        "hashtags": post.get("hashtags", []),
        "media_type": post.get("media_type"),
        "likes": post.get("metrics", {}).get("likes"),
        "comments": post.get("metrics", {}).get("comments"),
        "taken_at": post.get("taken_at"),
        "thumbnail_url": post.get("thumbnail_url"),
        "thumbnail_local_path": post.get("thumbnail_local_path"),
        "image_urls": post.get("image_urls", []),
        "image_local_paths": post.get("image_local_paths", []),
        "video_urls": post.get("video_urls", []),
        "video_local_paths": post.get("video_local_paths", []),
        "media_local_paths": post.get("media_local_paths", []),
        "media_assets": post.get("media_assets", []),
        "collected_at": extracted_at,
    }


def _build_comments(collected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    comment_map: dict[tuple[str | None, str | None, str | None], dict[str, Any]] = {}

    for bundle in collected.get("legacy_bundles", []):
        for comment in bundle.get("comments", []):
            comment_map[_comment_key(comment)] = comment
        for reply in bundle.get("replies", []):
            comment_map[_comment_key(reply)] = reply

    for item_doc in collected.get("item_docs", []):
        for comment in item_doc.get("comments", []):
            comment_map[_comment_key(comment)] = comment
        for reply in item_doc.get("replies", []):
            comment_map[_comment_key(reply)] = reply

    return list(comment_map.values())


def _comment_key(comment: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    post_ref = comment.get("post_ref") or {}
    return (
        comment.get("platform"),
        comment.get("comment_id"),
        post_ref.get("code") or post_ref.get("media_id"),
    )


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
    collected: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    post_dates = [post["taken_at"] for post in posts if post.get("taken_at")]
    collected_at_values = [
        *(bundle.get("collected_at") for bundle in collected.get("legacy_bundles", [])),
        *(account.get("extracted_at") for account in collected.get("account_docs", [])),
        *(item.get("extracted_at") for item in collected.get("item_docs", [])),
    ]
    valid_collected_at = [value for value in collected_at_values if value]
    return {
        "updated_at": max(valid_collected_at) if valid_collected_at else utc_now_iso(),
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


def _keep_latest(
    rows_by_key: dict[tuple[str | None, str | None, str | None], dict[str, Any]],
    key: tuple[str | None, str | None, str | None],
    row: dict[str, Any],
    timestamp: str | None,
) -> None:
    current = rows_by_key.get(key)
    if current is None or (timestamp or "") >= (current.get("collected_at") or ""):
        rows_by_key[key] = row


def _account_key(row: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    return (
        row.get("platform"),
        row.get("account_id") or row.get("username"),
        row.get("username"),
    )


def _post_key(row: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    return (
        row.get("platform"),
        row.get("post_id") or row.get("code"),
        row.get("code"),
    )
