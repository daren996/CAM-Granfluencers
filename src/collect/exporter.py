from __future__ import annotations

import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from .storage import utc_now_iso, write_json


DASHBOARD_EXPORT_FILES = {
    "site_summary": "site-summary.json",
    "accounts": "accounts.json",
    "posts": "posts.json",
    "comments": "comments.json",
    "hashtags": "hashtags.json",
    "engagement_timeseries": "engagement-timeseries.json",
    "collection_tree": "collection-tree.json",
}


def export_dashboard_data(
    input_path: str | Path, output_dir: str | Path = "data/dashboard"
) -> dict[str, str]:
    collected = load_collected_data(Path(input_path))
    output_path = Path(output_dir)
    account_docs = _collect_latest_account_documents(collected)
    item_docs = _collect_latest_item_documents(collected)
    account_docs = _ensure_account_documents(account_docs, item_docs)
    accounts = _build_accounts(account_docs)
    posts = _build_posts(item_docs)
    comments = _build_comments(item_docs)
    hashtags = _build_hashtags(posts)
    timeseries = _build_timeseries(posts)
    collection_tree = _build_collection_tree(account_docs, item_docs)
    site_summary = _build_site_summary(accounts, posts, comments, collection_tree, account_docs, item_docs)

    payloads = {
        "site_summary": site_summary,
        "accounts": accounts,
        "posts": posts,
        "comments": comments,
        "hashtags": hashtags,
        "engagement_timeseries": timeseries,
        "collection_tree": collection_tree,
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
    raw_profile_docs: list[dict[str, Any]] = []

    if path.is_file():
        payload = _load_json(path)
        if path.name == "bundle.json":
            legacy_bundles.append(payload)
        elif path.name == "account.json":
            account_docs.append(payload)
            item_docs.extend(_load_neighbor_item_docs(path.parent))
        elif path.name == "item.json":
            item_docs.append(payload)
        elif path.name == "profile.json" and path.parent == path.parent.parent / "account":
            raw_profile_docs.append(payload)
        else:
            raise ValueError(f"Unsupported collection input file: {path}")
        return {
            "legacy_bundles": legacy_bundles,
            "account_docs": account_docs,
            "item_docs": item_docs,
            "raw_profile_docs": raw_profile_docs,
        }

    legacy_bundles = [_load_json(bundle_path) for bundle_path in sorted(path.rglob("bundle.json"))]
    account_docs = [_load_json(account_path) for account_path in sorted(path.rglob("account.json"))]
    item_docs = [_load_json(item_path) for item_path in sorted(path.rglob("item.json"))]
    raw_profile_docs = [
        _load_json(profile_path) for profile_path in sorted(path.rglob("raw/account/profile.json"))
    ]
    return {
        "legacy_bundles": legacy_bundles,
        "account_docs": account_docs,
        "item_docs": item_docs,
        "raw_profile_docs": raw_profile_docs,
    }


def _load_neighbor_item_docs(account_dir: Path) -> list[dict[str, Any]]:
    return [_load_json(item_path) for item_path in sorted(account_dir.rglob("item.json"))]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_latest_account_documents(collected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    docs_by_key: dict[tuple[str | None, str | None, str | None], dict[str, Any]] = {}

    for bundle in collected.get("legacy_bundles", []):
        doc = _account_doc_from_bundle(bundle)
        _keep_latest(docs_by_key, _account_doc_key(doc), doc, _document_timestamp(doc))

    for account_doc in collected.get("account_docs", []):
        doc = _normalize_account_document(account_doc)
        _keep_latest(docs_by_key, _account_doc_key(doc), doc, _document_timestamp(doc))

    for raw_profile_doc in collected.get("raw_profile_docs", []):
        doc = _account_doc_from_raw_profile(raw_profile_doc)
        _keep_latest(docs_by_key, _account_doc_key(doc), doc, _document_timestamp(doc))

    docs = list(docs_by_key.values())
    docs.sort(key=_account_doc_sort_key)
    return docs


def _collect_latest_item_documents(collected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    docs_by_key: dict[tuple[str | None, str | None, str | None], dict[str, Any]] = {}

    for bundle in collected.get("legacy_bundles", []):
        for item_doc in _item_docs_from_bundle(bundle):
            _keep_latest(docs_by_key, _item_doc_key(item_doc), item_doc, _document_timestamp(item_doc))

    for item_doc in collected.get("item_docs", []):
        doc = _normalize_item_document(item_doc)
        _keep_latest(docs_by_key, _item_doc_key(doc), doc, _document_timestamp(doc))

    docs = list(docs_by_key.values())
    docs.sort(key=_item_doc_sort_key, reverse=True)
    return docs


def _ensure_account_documents(
    account_docs: list[dict[str, Any]], item_docs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    docs_by_key = {
        _account_doc_key(account_doc): deepcopy(account_doc) for account_doc in account_docs
    }
    hydration_keys = {
        key for key, account_doc in docs_by_key.items() if _needs_metric_hydration(account_doc)
    }

    for item_doc in item_docs:
        key = _account_doc_key_from_item(item_doc)
        target_doc = docs_by_key.get(key)
        if target_doc is None:
            target_doc = _synthetic_account_doc_from_item(item_doc)
            docs_by_key[key] = target_doc
            hydration_keys.add(key)
        if key in hydration_keys:
            _accumulate_item_metrics_into_account(target_doc, item_doc)

    merged_docs = list(docs_by_key.values())
    merged_docs.sort(key=_account_doc_sort_key)
    return merged_docs


def _normalize_account_document(account_doc: dict[str, Any]) -> dict[str, Any]:
    doc = deepcopy(account_doc)
    profile = doc.get("profile") or {}
    platform = doc.get("platform") or profile.get("platform") or _platform_from_account_ref(
        doc.get("account_ref")
    )
    account_ref = deepcopy(doc.get("account_ref") or _account_ref_from_profile(profile, platform))

    doc["platform"] = platform
    doc["account_ref"] = account_ref
    doc["profile"] = deepcopy(profile)
    doc["metrics"] = deepcopy(doc.get("metrics") or {})
    doc["request_log"] = deepcopy(doc.get("request_log") or [])
    doc["output_paths"] = deepcopy(doc.get("output_paths") or {})
    doc["include_comments"] = bool(doc.get("include_comments", False))
    return doc


def _normalize_item_document(item_doc: dict[str, Any]) -> dict[str, Any]:
    doc = deepcopy(item_doc)
    post = deepcopy(doc.get("post") or {})
    platform = doc.get("platform") or post.get("platform") or _platform_from_account_ref(
        doc.get("account_ref")
    )
    account_ref = deepcopy(doc.get("account_ref") or _account_ref_from_post(post, platform))

    doc["platform"] = platform
    doc["account_ref"] = account_ref
    doc["post"] = post
    doc["item_type"] = doc.get("item_type") or post.get("item_type") or "post"
    doc["item_key"] = doc.get("item_key") or _post_slug(post)
    doc["comments"] = deepcopy(doc.get("comments") or [])
    doc["replies"] = deepcopy(doc.get("replies") or [])
    doc["request_log"] = deepcopy(doc.get("request_log") or [])
    doc["output_paths"] = deepcopy(doc.get("output_paths") or {})
    return doc


def _account_doc_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    profile = deepcopy(bundle.get("profile") or {})
    platform = bundle.get("platform") or profile.get("platform")
    posts = bundle.get("posts") or []

    stored_posts = 0
    stored_reels = 0
    stored_likes = 0
    stored_comments = 0
    stored_plays = 0
    for post in posts:
        item_type = _item_type_from_post(post)
        if item_type == "reel":
            stored_reels += 1
        else:
            stored_posts += 1
        metrics = post.get("metrics") or {}
        stored_likes += int(metrics.get("likes") or 0)
        stored_comments += int(metrics.get("comments") or 0)
        stored_plays += int(metrics.get("plays") or 0)

    return {
        "platform": platform,
        "account_ref": deepcopy(bundle.get("account_ref") or _account_ref_from_profile(profile, platform)),
        "extracted_at": bundle.get("collected_at"),
        "include_comments": bool(bundle.get("include_comments", False)),
        "profile": profile,
        "metrics": {
            "stored_items": stored_posts + stored_reels,
            "stored_posts": stored_posts,
            "stored_reels": stored_reels,
            "stored_likes": stored_likes,
            "stored_comments": stored_comments,
            "stored_plays": stored_plays,
        },
        "request_log": deepcopy(bundle.get("request_log") or []),
        "output_paths": deepcopy(bundle.get("output_paths") or {}),
    }


def _account_doc_from_raw_profile(raw_profile_doc: dict[str, Any]) -> dict[str, Any]:
    profile = _profile_from_raw_profile(raw_profile_doc)
    platform = profile.get("platform")
    return {
        "platform": platform,
        "account_ref": _account_ref_from_profile(profile, platform),
        "extracted_at": _request_meta_from_raw_payload(
            "/api/v1/instagram/v3/get_user_profile",
            raw_profile_doc.get("params") or {},
            raw_profile_doc,
        ).get("fetched_at"),
        "include_comments": False,
        "profile": profile,
        "metrics": {},
        "request_log": [],
        "output_paths": {},
    }


def _synthetic_account_doc_from_item(item_doc: dict[str, Any]) -> dict[str, Any]:
    post = item_doc.get("post") or {}
    author = post.get("author") or {}
    platform = item_doc.get("platform") or post.get("platform")
    account_ref = deepcopy(item_doc.get("account_ref") or _account_ref_from_post(post, platform))
    return {
        "platform": platform,
        "account_ref": account_ref,
        "extracted_at": _document_timestamp(item_doc),
        "include_comments": bool(item_doc.get("comments") or item_doc.get("replies")),
        "profile": {
            "platform": platform,
            "account_id": author.get("account_id") or account_ref.get("user_id"),
            "username": author.get("username") or account_ref.get("username"),
            "full_name": author.get("full_name"),
            "is_verified": author.get("is_verified"),
            "raw_ids": {},
            "request_meta": {},
        },
        "metrics": {
            "stored_items": 0,
            "stored_posts": 0,
            "stored_reels": 0,
            "stored_likes": 0,
            "stored_comments": 0,
            "stored_plays": 0,
        },
        "request_log": [],
        "output_paths": {
            "account_dir": (item_doc.get("output_paths") or {}).get("account_dir"),
        },
    }


def _accumulate_item_metrics_into_account(account_doc: dict[str, Any], item_doc: dict[str, Any]) -> None:
    metrics = account_doc.setdefault("metrics", {})
    post = item_doc.get("post") or {}
    post_metrics = post.get("metrics") or {}
    item_type = item_doc.get("item_type") or post.get("item_type") or "post"

    metrics["stored_items"] = int(metrics.get("stored_items") or 0) + 1
    metrics.setdefault("stored_posts", 0)
    metrics.setdefault("stored_reels", 0)
    metrics.setdefault("stored_likes", 0)
    metrics.setdefault("stored_comments", 0)
    metrics.setdefault("stored_plays", 0)
    if item_type == "reel":
        metrics["stored_reels"] = int(metrics.get("stored_reels") or 0) + 1
    else:
        metrics["stored_posts"] = int(metrics.get("stored_posts") or 0) + 1
    metrics["stored_likes"] = int(metrics.get("stored_likes") or 0) + int(post_metrics.get("likes") or 0)
    metrics["stored_comments"] = int(metrics.get("stored_comments") or 0) + int(
        post_metrics.get("comments") or 0
    )
    metrics["stored_plays"] = int(metrics.get("stored_plays") or 0) + int(post_metrics.get("plays") or 0)
    account_doc["include_comments"] = bool(
        account_doc.get("include_comments") or item_doc.get("comments") or item_doc.get("replies")
    )
    item_timestamp = _document_timestamp(item_doc)
    if (item_timestamp or "") >= (_document_timestamp(account_doc) or ""):
        account_doc["extracted_at"] = item_timestamp


def _needs_metric_hydration(account_doc: dict[str, Any]) -> bool:
    metrics = account_doc.get("metrics") or {}
    return not any(
        metrics.get(field) is not None
        for field in (
            "stored_items",
            "stored_posts",
            "stored_reels",
            "stored_likes",
            "stored_comments",
            "stored_plays",
        )
    )


def _item_docs_from_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    comments_index: dict[tuple[str | None, str, str], list[dict[str, Any]]] = defaultdict(list)
    replies_index: dict[tuple[str | None, str, str], list[dict[str, Any]]] = defaultdict(list)

    for comment in bundle.get("comments") or []:
        _index_comment_record(comments_index, comment)
    for reply in bundle.get("replies") or []:
        _index_comment_record(replies_index, reply)

    item_docs: list[dict[str, Any]] = []
    platform = bundle.get("platform")
    account_ref = deepcopy(bundle.get("account_ref") or {})
    extracted_at = bundle.get("collected_at")

    for post in bundle.get("posts") or []:
        normalized_post = deepcopy(post)
        post_platform = normalized_post.get("platform") or platform
        item_docs.append(
            {
                "platform": post_platform,
                "account_ref": deepcopy(account_ref) or _account_ref_from_post(normalized_post, post_platform),
                "item_type": _item_type_from_post(normalized_post),
                "item_key": _post_slug(normalized_post),
                "extracted_at": extracted_at,
                "post": normalized_post,
                "comments": _collect_comments_for_post(comments_index, normalized_post),
                "replies": _collect_comments_for_post(replies_index, normalized_post),
                "request_log": [],
                "output_paths": {},
            }
        )

    return item_docs


def _build_accounts(account_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_account_row(doc) for doc in account_docs]


def _account_row(account_doc: dict[str, Any]) -> dict[str, Any]:
    profile = account_doc.get("profile") or {}
    metrics = account_doc.get("metrics") or {}
    extracted_at = _document_timestamp(account_doc)
    return {
        "platform": profile.get("platform") or account_doc.get("platform"),
        "account_id": profile.get("account_id"),
        "username": profile.get("username"),
        "full_name": profile.get("full_name"),
        "biography": profile.get("biography"),
        "external_url": profile.get("external_url"),
        "profile_pic_url": profile.get("profile_pic_url"),
        "profile_pic_local_path": profile.get("profile_pic_local_path"),
        "profile_pic_download": profile.get("profile_pic_download"),
        "profile_pic_download_error": profile.get("profile_pic_download_error"),
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
        "stored_plays": metrics.get("stored_plays"),
        "raw_ids": profile.get("raw_ids"),
        "request_meta": profile.get("request_meta"),
        "account_ref": account_doc.get("account_ref"),
        "include_comments": account_doc.get("include_comments", False),
        "metrics": metrics,
        "profile": profile,
        "request_log": account_doc.get("request_log", []),
        "output_paths": account_doc.get("output_paths", {}),
        "extracted_at": extracted_at,
        "collected_at": extracted_at,
    }


def _build_posts(item_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_post_row(item_doc) for item_doc in item_docs]


def _post_row(item_doc: dict[str, Any]) -> dict[str, Any]:
    post = item_doc.get("post") or {}
    metrics = post.get("metrics") or {}
    author = post.get("author") or {}
    extracted_at = _document_timestamp(item_doc)
    return {
        "platform": post.get("platform") or item_doc.get("platform"),
        "post_id": post.get("post_id"),
        "code": post.get("code"),
        "url": post.get("url"),
        "item_type": item_doc.get("item_type") or post.get("item_type") or "post",
        "item_key": item_doc.get("item_key"),
        "account_ref": item_doc.get("account_ref"),
        "account_id": author.get("account_id"),
        "username": author.get("username"),
        "author": author,
        "caption": post.get("caption"),
        "hashtags": post.get("hashtags", []),
        "media_type": post.get("media_type"),
        "likes": metrics.get("likes"),
        "comments": metrics.get("comments"),
        "plays": metrics.get("plays"),
        "metrics": metrics,
        "taken_at": post.get("taken_at"),
        "thumbnail_url": post.get("thumbnail_url"),
        "thumbnail_local_path": post.get("thumbnail_local_path"),
        "image_urls": post.get("image_urls", []),
        "image_local_paths": post.get("image_local_paths", []),
        "video_urls": post.get("video_urls", []),
        "video_local_paths": post.get("video_local_paths", []),
        "media_local_paths": post.get("media_local_paths", []),
        "media_assets": post.get("media_assets", []),
        "raw_ids": post.get("raw_ids"),
        "request_meta": post.get("request_meta"),
        "request_log": item_doc.get("request_log", []),
        "output_paths": item_doc.get("output_paths", {}),
        "comment_records_count": len(item_doc.get("comments") or []),
        "reply_records_count": len(item_doc.get("replies") or []),
        "extracted_at": extracted_at,
        "collected_at": extracted_at,
    }


def _build_comments(item_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item_doc in item_docs:
        post = item_doc.get("post") or {}
        for comment in item_doc.get("comments") or []:
            rows.append(_comment_row(comment, item_doc, post, comment_type="comment"))
        for reply in item_doc.get("replies") or []:
            rows.append(_comment_row(reply, item_doc, post, comment_type="reply"))

    rows.sort(
        key=lambda row: (
            row.get("created_at") or "",
            row.get("comment_id") or "",
        ),
        reverse=True,
    )
    return rows


def _comment_row(
    comment: dict[str, Any],
    item_doc: dict[str, Any],
    post: dict[str, Any],
    *,
    comment_type: str,
) -> dict[str, Any]:
    user = comment.get("user") or {}
    author = post.get("author") or {}
    extracted_at = _document_timestamp(item_doc)
    creator_match = False
    if user and author:
        creator_match = bool(
            user.get("account_id")
            and author.get("account_id")
            and user.get("account_id") == author.get("account_id")
        ) or bool(
            user.get("username")
            and author.get("username")
            and user.get("username") == author.get("username")
        )

    return {
        "platform": comment.get("platform") or item_doc.get("platform"),
        "comment_type": comment_type,
        "item_type": item_doc.get("item_type"),
        "item_key": item_doc.get("item_key"),
        "account_ref": item_doc.get("account_ref"),
        "post_id": post.get("post_id"),
        "post_code": post.get("code"),
        "post_url": post.get("url"),
        "post_taken_at": post.get("taken_at"),
        "post_account_id": author.get("account_id"),
        "post_username": author.get("username"),
        "comment_id": comment.get("comment_id"),
        "parent_comment_id": comment.get("parent_comment_id"),
        "text": comment.get("text"),
        "created_at": comment.get("created_at"),
        "like_count": comment.get("like_count"),
        "child_comment_count": comment.get("child_comment_count"),
        "is_creator_interaction": creator_match,
        "user": user,
        "user_account_id": user.get("account_id"),
        "user_username": user.get("username"),
        "user_full_name": user.get("full_name"),
        "user_is_verified": user.get("is_verified"),
        "raw_ids": comment.get("raw_ids"),
        "request_meta": comment.get("request_meta"),
        "extracted_at": extracted_at,
    }


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
        lambda: {
            "date": None,
            "items": 0,
            "posts": 0,
            "reels": 0,
            "likes": 0,
            "comments": 0,
            "plays": 0,
        }
    )
    for post in posts:
        taken_at = post.get("taken_at")
        if not taken_at:
            continue
        date = taken_at[:10]
        bucket = buckets[date]
        bucket["date"] = date
        bucket["items"] += 1
        if post.get("item_type") == "reel":
            bucket["reels"] += 1
        else:
            bucket["posts"] += 1
        bucket["likes"] += int(post.get("likes") or 0)
        bucket["comments"] += int(post.get("comments") or 0)
        bucket["plays"] += int(post.get("plays") or 0)
    return [buckets[key] for key in sorted(buckets)]


def _build_collection_tree(
    account_docs: list[dict[str, Any]], item_docs: list[dict[str, Any]]
) -> dict[str, Any]:
    platforms: dict[str, dict[str, Any]] = {}

    for account_doc in account_docs:
        platform = str(account_doc.get("platform") or "unknown")
        platform_node = platforms.setdefault(platform, {"platform": platform, "accounts": []})
        account_node = {
            "platform": platform,
            "account_key": _account_tree_key(account_doc),
            "account_ref": deepcopy(account_doc.get("account_ref") or {}),
            "extracted_at": _document_timestamp(account_doc),
            "include_comments": bool(account_doc.get("include_comments", False)),
            "profile": deepcopy(account_doc.get("profile") or {}),
            "metrics": deepcopy(account_doc.get("metrics") or {}),
            "request_log": deepcopy(account_doc.get("request_log") or []),
            "output_paths": deepcopy(account_doc.get("output_paths") or {}),
            "items": [],
        }
        platform_node["accounts"].append(account_node)

    for item_doc in item_docs:
        platform = str(item_doc.get("platform") or "unknown")
        platform_node = platforms.setdefault(platform, {"platform": platform, "accounts": []})
        account_key = _account_tree_key(item_doc)
        account_node = _find_or_create_account_node(platform_node, item_doc, account_key)
        account_node["items"].append(_item_tree_node(item_doc))

    platform_nodes: list[dict[str, Any]] = []
    for platform_name in sorted(platforms):
        platform_node = platforms[platform_name]
        platform_accounts = platform_node["accounts"]
        for account_node in platform_accounts:
            account_node["items"].sort(key=_item_tree_sort_key, reverse=True)
            account_node["summary"] = _account_tree_summary(account_node["items"])
        platform_accounts.sort(key=_account_tree_sort_key)
        platform_node["summary"] = _platform_tree_summary(platform_accounts)
        platform_nodes.append(platform_node)

    counts = {
        "platforms": len(platform_nodes),
        "accounts": sum(len(platform_node["accounts"]) for platform_node in platform_nodes),
        "items": sum(platform_node["summary"]["items"] for platform_node in platform_nodes),
        "posts": sum(platform_node["summary"]["posts"] for platform_node in platform_nodes),
        "reels": sum(platform_node["summary"]["reels"] for platform_node in platform_nodes),
        "comments": sum(platform_node["summary"]["comments"] for platform_node in platform_nodes),
        "replies": sum(platform_node["summary"]["replies"] for platform_node in platform_nodes),
    }

    return {
        "updated_at": _latest_timestamp([*account_docs, *item_docs]),
        "counts": counts,
        "platforms": platform_nodes,
    }


def _find_or_create_account_node(
    platform_node: dict[str, Any], item_doc: dict[str, Any], account_key: str
) -> dict[str, Any]:
    for account_node in platform_node["accounts"]:
        if account_node.get("account_key") == account_key:
            return account_node

    post = item_doc.get("post") or {}
    author = post.get("author") or {}
    account_ref = deepcopy(item_doc.get("account_ref") or {})
    profile = {
        "platform": item_doc.get("platform"),
        "account_id": author.get("account_id") or account_ref.get("user_id"),
        "username": author.get("username") or account_ref.get("username"),
        "full_name": author.get("full_name"),
        "is_verified": author.get("is_verified"),
        "raw_ids": {},
        "request_meta": {},
    }
    account_node = {
        "platform": item_doc.get("platform"),
        "account_key": account_key,
        "account_ref": account_ref,
        "extracted_at": _document_timestamp(item_doc),
        "include_comments": bool(item_doc.get("comments") or item_doc.get("replies")),
        "profile": profile,
        "metrics": {},
        "request_log": [],
        "output_paths": {
            "account_dir": (item_doc.get("output_paths") or {}).get("account_dir"),
        },
        "items": [],
    }
    platform_node["accounts"].append(account_node)
    return account_node


def _item_tree_node(item_doc: dict[str, Any]) -> dict[str, Any]:
    post = deepcopy(item_doc.get("post") or {})
    comments = deepcopy(item_doc.get("comments") or [])
    replies = deepcopy(item_doc.get("replies") or [])
    metrics = post.get("metrics") or {}
    return {
        "platform": item_doc.get("platform"),
        "account_ref": deepcopy(item_doc.get("account_ref") or {}),
        "item_type": item_doc.get("item_type"),
        "item_key": item_doc.get("item_key"),
        "extracted_at": _document_timestamp(item_doc),
        "summary": {
            "media_assets": len(post.get("media_assets") or []),
            "comments": len(comments),
            "replies": len(replies),
            "likes": metrics.get("likes"),
            "comment_total": metrics.get("comments"),
            "plays": metrics.get("plays"),
        },
        "post": post,
        "comments": comments,
        "replies": replies,
        "comment_threads": _build_comment_threads(comments, replies),
        "request_log": deepcopy(item_doc.get("request_log") or []),
        "output_paths": deepcopy(item_doc.get("output_paths") or {}),
    }


def _build_comment_threads(
    comments: list[dict[str, Any]], replies: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    replies_by_parent: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for reply in replies:
        replies_by_parent[reply.get("parent_comment_id")].append(reply)

    threads: list[dict[str, Any]] = []
    seen_parent_ids: set[str | None] = set()
    for comment in sorted(comments, key=_comment_sort_key):
        comment_id = comment.get("comment_id")
        seen_parent_ids.add(comment_id)
        thread_replies = sorted(replies_by_parent.get(comment_id, []), key=_comment_sort_key)
        threads.append(
            {
                "comment": deepcopy(comment),
                "replies": deepcopy(thread_replies),
            }
        )

    for parent_id, orphan_replies in sorted(replies_by_parent.items(), key=lambda item: str(item[0] or "")):
        if parent_id in seen_parent_ids:
            continue
        threads.append(
            {
                "comment": None,
                "parent_comment_id": parent_id,
                "replies": deepcopy(sorted(orphan_replies, key=_comment_sort_key)),
            }
        )

    return threads


def _build_site_summary(
    accounts: list[dict[str, Any]],
    posts: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    collection_tree: dict[str, Any],
    account_docs: list[dict[str, Any]],
    item_docs: list[dict[str, Any]],
) -> dict[str, Any]:
    post_dates = [post["taken_at"] for post in posts if post.get("taken_at")]
    reply_count = sum(1 for comment in comments if comment.get("comment_type") == "reply")
    return {
        "updated_at": _latest_timestamp([*account_docs, *item_docs]),
        "project_status": "ready_with_data" if posts else "waiting_for_data",
        "counts": {
            "platforms": len(collection_tree.get("platforms") or []),
            "accounts": len(accounts),
            "items": len(posts),
            "posts": sum(1 for post in posts if post.get("item_type") != "reel"),
            "reels": sum(1 for post in posts if post.get("item_type") == "reel"),
            "comments": len(comments),
            "top_level_comments": len(comments) - reply_count,
            "replies": reply_count,
        },
        "date_range": {
            "start": min(post_dates) if post_dates else None,
            "end": max(post_dates) if post_dates else None,
        },
    }


def _index_comment_record(
    index: dict[tuple[str | None, str, str], list[dict[str, Any]]], comment: dict[str, Any]
) -> None:
    platform = comment.get("platform")
    post_ref = comment.get("post_ref") or {}
    for field in ("code", "media_id", "url"):
        value = post_ref.get(field)
        if value:
            index[(platform, field, str(value))].append(deepcopy(comment))


def _collect_comments_for_post(
    index: dict[tuple[str | None, str, str], list[dict[str, Any]]], post: dict[str, Any]
) -> list[dict[str, Any]]:
    seen: set[tuple[str | None, str | None, str | None]] = set()
    comments: list[dict[str, Any]] = []
    platform = post.get("platform")
    keys = [
        (platform, "code", str(post.get("code"))) if post.get("code") else None,
        (platform, "media_id", str(post.get("post_id"))) if post.get("post_id") else None,
        (platform, "url", str(post.get("url"))) if post.get("url") else None,
    ]
    for key in [key for key in keys if key]:
        for comment in index.get(key, []):
            comment_key = _comment_identity(comment)
            if comment_key in seen:
                continue
            seen.add(comment_key)
            comments.append(deepcopy(comment))
    comments.sort(key=_comment_sort_key)
    return comments


def _comment_identity(comment: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    return (
        comment.get("platform"),
        comment.get("comment_id"),
        comment.get("parent_comment_id"),
    )


def _profile_from_raw_profile(raw_profile_doc: dict[str, Any]) -> dict[str, Any]:
    user = ((raw_profile_doc.get("data") or {}).get("user")) or {}
    return {
        "platform": "instagram",
        "account_id": _stringify(user.get("id") or user.get("pk")),
        "username": user.get("username"),
        "full_name": user.get("full_name"),
        "biography": user.get("biography"),
        "external_url": user.get("external_url"),
        "profile_pic_url": ((user.get("hd_profile_pic_url_info") or {}).get("url"))
        or user.get("profile_pic_url"),
        "is_verified": bool(user.get("is_verified")),
        "is_private": bool(user.get("is_private")),
        "followers_count": user.get("follower_count"),
        "following_count": user.get("following_count"),
        "posts_count": user.get("media_count"),
        "reels_count": user.get("total_clips_count"),
        "raw_ids": {"user_id": _stringify(user.get("id") or user.get("pk"))},
        "request_meta": _request_meta_from_raw_payload(
            "/api/v1/instagram/v3/get_user_profile",
            raw_profile_doc.get("params") or {},
            raw_profile_doc,
        ),
    }


def _request_meta_from_raw_payload(
    default_endpoint: str, params: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    router = payload.get("router") or default_endpoint
    return {
        "source_endpoint": router,
        "request_url": None,
        "request_params": params,
        "fetched_at": payload.get("time"),
        "request_id": payload.get("request_id"),
        "router": router,
        "docs": payload.get("docs"),
        "cache_url": payload.get("cache_url"),
        "cache_message": payload.get("cache_message"),
        "cache_message_zh": payload.get("cache_message_zh"),
    }


def _stringify(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _account_doc_key(account_doc: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    profile = account_doc.get("profile") or {}
    account_ref = account_doc.get("account_ref") or {}
    platform = account_doc.get("platform") or profile.get("platform") or account_ref.get("platform")
    account_id = profile.get("account_id") or account_ref.get("user_id")
    username = profile.get("username") or account_ref.get("username")
    return (
        platform,
        account_id or username,
        username,
    )


def _account_doc_key_from_item(item_doc: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    post = item_doc.get("post") or {}
    author = post.get("author") or {}
    account_ref = item_doc.get("account_ref") or {}
    platform = item_doc.get("platform") or post.get("platform") or account_ref.get("platform")
    account_id = author.get("account_id") or account_ref.get("user_id")
    username = author.get("username") or account_ref.get("username")
    return (
        platform,
        account_id or username,
        username,
    )


def _item_doc_key(item_doc: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    post = item_doc.get("post") or {}
    return (
        item_doc.get("platform") or post.get("platform"),
        post.get("post_id") or item_doc.get("item_key") or post.get("code"),
        post.get("code") or item_doc.get("item_key"),
    )


def _document_timestamp(document: dict[str, Any]) -> str | None:
    return document.get("extracted_at") or document.get("collected_at")


def _latest_timestamp(documents: list[dict[str, Any]]) -> str:
    timestamps = [timestamp for timestamp in (_document_timestamp(doc) for doc in documents) if timestamp]
    return max(timestamps) if timestamps else utc_now_iso()


def _platform_from_account_ref(account_ref: dict[str, Any] | None) -> str | None:
    if not account_ref:
        return None
    return account_ref.get("platform")


def _account_ref_from_profile(profile: dict[str, Any], platform: str | None) -> dict[str, Any]:
    return {
        "platform": platform,
        "username": profile.get("username"),
        "user_id": profile.get("account_id"),
    }


def _account_ref_from_post(post: dict[str, Any], platform: str | None) -> dict[str, Any]:
    author = post.get("author") or {}
    return {
        "platform": platform,
        "username": author.get("username"),
        "user_id": author.get("account_id"),
    }


def _item_type_from_post(post: dict[str, Any]) -> str:
    return post.get("item_type") or ("reel" if (post.get("raw_ids") or {}).get("product_type") in {"clips", "igtv", "reels"} else "post")


def _post_slug(post: dict[str, Any]) -> str:
    return str(post.get("code") or post.get("post_id") or "post")


def _account_doc_sort_key(account_doc: dict[str, Any]) -> tuple[str, str]:
    profile = account_doc.get("profile") or {}
    return (
        str(profile.get("username") or ""),
        str(profile.get("account_id") or ""),
    )


def _item_doc_sort_key(item_doc: dict[str, Any]) -> tuple[str, str]:
    post = item_doc.get("post") or {}
    return (
        str(post.get("taken_at") or ""),
        str(_document_timestamp(item_doc) or ""),
    )


def _comment_sort_key(comment: dict[str, Any]) -> tuple[str, str]:
    return (
        str(comment.get("created_at") or ""),
        str(comment.get("comment_id") or ""),
    )


def _account_tree_key(document: dict[str, Any]) -> str:
    if "profile" in document:
        profile = document.get("profile") or {}
        account_ref = document.get("account_ref") or {}
    else:
        post = document.get("post") or {}
        author = post.get("author") or {}
        profile = {
            "account_id": author.get("account_id"),
            "username": author.get("username"),
        }
        account_ref = document.get("account_ref") or {}

    return str(
        profile.get("account_id")
        or account_ref.get("user_id")
        or profile.get("username")
        or account_ref.get("username")
        or "account"
    )


def _account_tree_sort_key(account_node: dict[str, Any]) -> tuple[str, str]:
    profile = account_node.get("profile") or {}
    return (
        str(profile.get("username") or ""),
        str(profile.get("account_id") or ""),
    )


def _item_tree_sort_key(item_node: dict[str, Any]) -> tuple[str, str]:
    post = item_node.get("post") or {}
    return (
        str(post.get("taken_at") or ""),
        str(item_node.get("extracted_at") or ""),
    )


def _account_tree_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "items": len(items),
        "posts": sum(1 for item in items if item.get("item_type") != "reel"),
        "reels": sum(1 for item in items if item.get("item_type") == "reel"),
        "comments": sum(len(item.get("comments") or []) for item in items),
        "replies": sum(len(item.get("replies") or []) for item in items),
    }


def _platform_tree_summary(accounts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accounts": len(accounts),
        "items": sum((account.get("summary") or {}).get("items", 0) for account in accounts),
        "posts": sum((account.get("summary") or {}).get("posts", 0) for account in accounts),
        "reels": sum((account.get("summary") or {}).get("reels", 0) for account in accounts),
        "comments": sum((account.get("summary") or {}).get("comments", 0) for account in accounts),
        "replies": sum((account.get("summary") or {}).get("replies", 0) for account in accounts),
    }


def _keep_latest(
    rows_by_key: dict[tuple[str | None, str | None, str | None], dict[str, Any]],
    key: tuple[str | None, str | None, str | None],
    row: dict[str, Any],
    timestamp: str | None,
) -> None:
    current = rows_by_key.get(key)
    if current is None or (timestamp or "") >= (_document_timestamp(current) or current.get("collected_at") or ""):
        rows_by_key[key] = row
