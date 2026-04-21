from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .client import TikHubClient
from .instagram import InstagramCollector
from .models import AccountRef, PostRef
from .storage import (
    DownloadedAsset,
    download_remote_asset,
    make_account_dir,
    utc_now_iso,
    write_json,
    write_raw_json,
    write_raw_snapshot,
)

LogFn = Callable[[str], None]
MediaDownloader = Callable[..., DownloadedAsset]


def get_collector(platform: str, client: TikHubClient | None = None):
    resolved_platform = platform.lower()
    client = client or TikHubClient()
    if resolved_platform == "instagram":
        return InstagramCollector(client)
    raise ValueError(f"Unsupported platform: {platform}")


def collect_account_bundle(
    account_ref: AccountRef,
    include_comments: bool = False,
    max_posts: int | None = None,
    max_comment_pages: int | None = None,
    *,
    page_size: int | None = None,
    output_root: str | Path = "data/collect",
    client: TikHubClient | None = None,
    log: LogFn | None = None,
    media_downloader: MediaDownloader | None = None,
) -> dict[str, Any]:
    collector = get_collector(account_ref.platform, client=client)
    resolved_media_downloader = media_downloader or download_remote_asset
    extracted_at = utc_now_iso()
    _emit_log(
        log,
        f"Starting collection for {collector.platform}/{account_ref.slug} "
        f"(comments={'on' if include_comments else 'off'}).",
    )

    _emit_log(log, "Fetching account profile...")
    profile = collector.fetch_account_profile(account_ref)
    resolved_account_ref = _resolve_account_ref(account_ref, profile.record)
    account_dir = make_account_dir(output_root, collector.platform, resolved_account_ref.slug)
    request_log = [profile.request_meta]
    item_paths: list[str] = []

    _emit_log(log, f"Account directory: {account_dir}")
    write_raw_snapshot(account_dir, category="account", name="profile", payload=profile.raw_payload)
    _emit_log(log, "Saved account profile snapshot.")
    if resolved_account_ref.to_params() != account_ref.to_params():
        resolved_slug = resolved_account_ref.username or resolved_account_ref.user_id
        _emit_log(log, f"Resolved account reference to {resolved_slug}.")
    _download_profile_media(
        profile.record,
        account_dir,
        log=log,
        media_downloader=resolved_media_downloader,
    )

    posts: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    replies: list[dict[str, Any]] = []

    post_cursor = None
    page_index = 0
    while True:
        page_index += 1
        _emit_log(log, f"Fetching account posts page {page_index}...")
        page = collector.fetch_account_posts(
            resolved_account_ref,
            cursor=post_cursor,
            page_size=page_size,
        )
        request_log.append(page.request_meta)
        write_raw_snapshot(
            account_dir,
            category="account_posts",
            name=f"page-{page_index:03d}",
            payload=page.raw_payload,
        )
        page_records = page.records
        if max_posts is not None:
            remaining = max_posts - len(posts)
            page_records = page_records[: max(remaining, 0)]
        posts.extend(page_records)
        _emit_log(log, f"Collected {len(posts)} item(s) so far.")
        if max_posts is not None and len(posts) >= max_posts:
            break
        if not page.has_next_page or not page.next_cursor:
            break
        post_cursor = page.next_cursor

    enriched_posts: list[dict[str, Any]] = []
    for index, post in enumerate(posts, start=1):
        post_slug = _item_slug(post)
        post_ref = PostRef(
            platform=collector.platform,
            media_id=post["post_id"],
            shortcode=post.get("code"),
            url=post.get("url"),
        )
        _emit_log(log, f"Fetching item detail {index}/{len(posts)} for {post_slug}...")
        detail = collector.fetch_post_detail(post_ref)
        request_log.append(detail.request_meta)

        merged_post = _merge_post_records(post, detail.record)
        item_group = _item_group(merged_post)
        item_dir = account_dir / item_group / post_slug
        write_raw_json(item_dir, "detail.json", detail.raw_payload)

        _download_post_media(
            merged_post,
            item_dir,
            log=log,
            media_downloader=resolved_media_downloader,
        )

        item_comments: list[dict[str, Any]] = []
        item_replies: list[dict[str, Any]] = []
        item_request_log: list[dict[str, Any]] = [detail.request_meta]
        if include_comments:
            _emit_log(log, f"Collecting comments for {post_slug}...")
            _collect_comments_for_post(
                collector,
                post_ref,
                item_comments,
                item_replies,
                item_request_log,
                item_dir,
                max_comment_pages=max_comment_pages,
                log=log,
            )
            comments.extend(item_comments)
            replies.extend(item_replies)

        item_document = {
            "platform": collector.platform,
            "account_ref": resolved_account_ref.to_params() | {"platform": collector.platform},
            "item_type": item_group[:-1],
            "item_key": post_slug,
            "extracted_at": extracted_at,
            "post": merged_post,
            "comments": item_comments,
            "replies": item_replies,
            "request_log": item_request_log,
            "output_paths": {},
        }
        item_path = write_json(item_dir / "item.json", item_document)
        item_document["output_paths"] = {
            "account_dir": str(account_dir),
            "item_dir": str(item_dir),
            "item": str(item_path),
            "raw_dir": str(item_dir / "raw"),
            "media_dir": str(item_dir / "media"),
        }
        write_json(item_dir / "item.json", item_document)
        item_paths.append(str(item_path))
        enriched_posts.append(merged_post)

    account_document = {
        "platform": collector.platform,
        "account_ref": resolved_account_ref.to_params() | {"platform": collector.platform},
        "extracted_at": extracted_at,
        "include_comments": include_comments,
        "profile": profile.record,
        "metrics": _build_account_metrics(account_dir),
        "request_log": request_log,
        "output_paths": {},
    }
    _emit_log(log, "Writing account.json...")
    account_path = write_json(account_dir / "account.json", account_document)
    account_document["output_paths"] = {
        "account_dir": str(account_dir),
        "account": str(account_path),
        "raw_dir": str(account_dir / "raw"),
        "media_dir": str(account_dir / "media"),
        "items": item_paths,
    }
    write_json(account_dir / "account.json", account_document)
    _emit_log(
        log,
        "Collection finished. "
        f"Items={len(enriched_posts)}, comments={len(comments)}, replies={len(replies)}.",
    )
    return {
        "platform": collector.platform,
        "account_ref": resolved_account_ref.to_params() | {"platform": collector.platform},
        "extracted_at": extracted_at,
        "include_comments": include_comments,
        "profile": profile.record,
        "posts": enriched_posts,
        "comments": comments,
        "replies": replies,
        "request_log": request_log,
        "output_paths": account_document["output_paths"],
    }


def _collect_comments_for_post(
    collector,
    post_ref: PostRef,
    comments: list[dict[str, Any]],
    replies: list[dict[str, Any]],
    request_log: list[dict[str, Any]],
    item_dir: Path,
    *,
    max_comment_pages: int | None,
    log: LogFn | None = None,
) -> None:
    cursor = None
    page_index = 0
    baseline_comments = len(comments)
    while True:
        page_index += 1
        _emit_log(log, f"Fetching comments page {page_index} for {post_ref.slug}...")
        page = collector.fetch_post_comments(post_ref, cursor=cursor)
        request_log.append(page.request_meta)
        write_raw_json(item_dir, Path("comments") / f"page-{page_index:03d}.json", page.raw_payload)
        comments.extend(page.records)
        _emit_log(
            log,
            f"Collected {len(comments) - baseline_comments} comment(s) for {post_ref.slug}.",
        )
        for comment in page.records:
            if int(comment.get("child_comment_count") or 0) > 0:
                _collect_replies_for_comment(
                    collector,
                    post_ref,
                    comment["comment_id"],
                    replies,
                    request_log,
                    item_dir,
                    max_comment_pages=max_comment_pages,
                    log=log,
                )
        if max_comment_pages is not None and page_index >= max_comment_pages:
            break
        if not page.has_next_page or not page.next_cursor:
            break
        cursor = page.next_cursor


def _collect_replies_for_comment(
    collector,
    post_ref: PostRef,
    comment_id: str,
    replies: list[dict[str, Any]],
    request_log: list[dict[str, Any]],
    item_dir: Path,
    *,
    max_comment_pages: int | None,
    log: LogFn | None = None,
) -> None:
    cursor = None
    page_index = 0
    baseline_replies = len(replies)
    while True:
        page_index += 1
        _emit_log(
            log,
            f"Fetching replies page {page_index} for comment {comment_id} on {post_ref.slug}...",
        )
        page = collector.fetch_comment_replies(post_ref, comment_id, cursor=cursor)
        request_log.append(page.request_meta)
        write_raw_json(
            item_dir,
            Path("replies") / f"{comment_id}-page-{page_index:03d}.json",
            page.raw_payload,
        )
        replies.extend(page.records)
        _emit_log(
            log,
            f"Collected {len(replies) - baseline_replies} reply record(s) for comment {comment_id}.",
        )
        if max_comment_pages is not None and page_index >= max_comment_pages:
            break
        if not page.has_next_page or not page.next_cursor:
            break
        cursor = page.next_cursor


def _merge_post_records(base: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    merged = {**base, **detail}
    merged["metrics"] = {
        **(base.get("metrics") or {}),
        **(detail.get("metrics") or {}),
    }
    merged["author"] = {
        **(base.get("author") or {}),
        **(detail.get("author") or {}),
    }
    merged["raw_ids"] = {
        **(base.get("raw_ids") or {}),
        **(detail.get("raw_ids") or {}),
    }
    return merged


def _resolve_account_ref(account_ref: AccountRef, profile_record: dict[str, Any]) -> AccountRef:
    resolved_username = profile_record.get("username") or account_ref.username
    resolved_user_id = None if resolved_username else profile_record.get("account_id") or account_ref.user_id
    return AccountRef(
        platform=account_ref.platform,
        username=resolved_username,
        user_id=resolved_user_id,
    )


def _emit_log(log: LogFn | None, message: str) -> None:
    if log is not None:
        log(message)


def _download_profile_media(
    profile: dict[str, Any],
    account_dir: Path,
    *,
    log: LogFn | None,
    media_downloader: MediaDownloader,
) -> None:
    profile_pic_url = profile.get("profile_pic_url")
    if not profile_pic_url:
        return

    _emit_log(log, "Downloading account profile image...")
    asset = _download_asset(
        media_downloader,
        profile_pic_url,
        account_dir / "media" / "account",
        stem="profile",
    )
    profile["profile_pic_local_path"] = asset.get("path")
    if asset.get("error"):
        profile["profile_pic_download_error"] = asset["error"]
    profile["profile_pic_download"] = asset


def _download_post_media(
    post: dict[str, Any],
    item_dir: Path,
    *,
    log: LogFn | None,
    media_downloader: MediaDownloader,
) -> None:
    media_assets = post.get("media_assets") or []
    if not media_assets:
        return

    post_slug = _item_slug(post)
    _emit_log(log, f"Downloading media assets for {post_slug}...")
    downloaded_assets: list[dict[str, Any]] = []
    media_local_paths: list[str] = []
    image_local_paths: list[str] = []
    video_local_paths: list[str] = []
    image_downloads: list[dict[str, Any]] = []
    video_downloads: list[dict[str, Any]] = []
    thumbnail_local_path: str | None = None

    for index, media_asset in enumerate(media_assets, start=1):
        media_type = media_asset.get("media_type") or "asset"
        primary_download = _download_asset(
            media_downloader,
            media_asset["url"],
            item_dir / "media",
            stem=f"{index:02d}-{media_type}",
        )
        enriched_asset = {
            **media_asset,
            "local_path": primary_download.get("path"),
            "download": primary_download,
        }

        if primary_download.get("path"):
            media_local_paths.append(primary_download["path"])

        if media_type == "image":
            if primary_download.get("path"):
                image_local_paths.append(primary_download["path"])
            image_downloads.append(enriched_asset)
            enriched_asset["thumbnail_local_path"] = primary_download.get("path")
        elif media_type == "video":
            if primary_download.get("path"):
                video_local_paths.append(primary_download["path"])
            video_downloads.append(enriched_asset)
            thumbnail_url = media_asset.get("thumbnail_url")
            if thumbnail_url and thumbnail_url != media_asset.get("url"):
                thumbnail_download = _download_asset(
                    media_downloader,
                    thumbnail_url,
                    item_dir / "media",
                    stem=f"{index:02d}-{media_type}-thumb",
                )
                enriched_asset["thumbnail_download"] = thumbnail_download
                enriched_asset["thumbnail_local_path"] = thumbnail_download.get("path")
            else:
                enriched_asset["thumbnail_local_path"] = primary_download.get("path")

        if not thumbnail_local_path and enriched_asset.get("thumbnail_local_path"):
            thumbnail_local_path = enriched_asset["thumbnail_local_path"]

        downloaded_assets.append(enriched_asset)

    post["media_assets"] = downloaded_assets
    post["media_local_paths"] = media_local_paths
    post["image_local_paths"] = image_local_paths
    post["video_local_paths"] = video_local_paths
    post["image_downloads"] = image_downloads
    post["video_downloads"] = video_downloads
    if thumbnail_local_path:
        post["thumbnail_local_path"] = thumbnail_local_path


def _download_asset(
    media_downloader: MediaDownloader,
    url: str,
    output_dir: Path,
    *,
    stem: str,
) -> dict[str, Any]:
    try:
        asset = media_downloader(url, output_dir, stem=stem)
    except Exception as exc:  # pragma: no cover - defensive against network/filesystem issues
        return {"source_url": url, "path": None, "error": str(exc)}

    return {
        "source_url": asset.source_url,
        "path": str(asset.path),
        "content_type": asset.content_type,
        "size_bytes": asset.size_bytes,
    }


def _build_account_metrics(account_dir: Path) -> dict[str, int]:
    stored_posts = 0
    stored_reels = 0
    stored_likes = 0
    stored_comments = 0
    stored_plays = 0

    for item_path in sorted(account_dir.glob("posts/*/item.json")):
        post = _load_item_post(item_path)
        if not post:
            continue
        stored_posts += 1
        stored_likes += int(post.get("metrics", {}).get("likes") or 0)
        stored_comments += int(post.get("metrics", {}).get("comments") or 0)
        stored_plays += int(post.get("metrics", {}).get("plays") or 0)

    for item_path in sorted(account_dir.glob("reels/*/item.json")):
        post = _load_item_post(item_path)
        if not post:
            continue
        stored_reels += 1
        stored_likes += int(post.get("metrics", {}).get("likes") or 0)
        stored_comments += int(post.get("metrics", {}).get("comments") or 0)
        stored_plays += int(post.get("metrics", {}).get("plays") or 0)

    return {
        "stored_items": stored_posts + stored_reels,
        "stored_posts": stored_posts,
        "stored_reels": stored_reels,
        "stored_likes": stored_likes,
        "stored_comments": stored_comments,
        "stored_plays": stored_plays,
    }


def _load_item_post(item_path: Path) -> dict[str, Any]:
    payload = json.loads(item_path.read_text(encoding="utf-8"))
    return payload.get("post") or {}


def _item_slug(post: dict[str, Any]) -> str:
    return str(post.get("code") or post.get("post_id") or "post")


def _item_group(post: dict[str, Any]) -> str:
    if post.get("item_type") == "reel":
        return "reels"
    return "posts"
