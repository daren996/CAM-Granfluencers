from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from .client import TikHubClient
from .exporter import export_dashboard_data
from .instagram import InstagramCollector
from .models import AccountRef, CollectionBundle, PostRef
from .storage import make_run_dir, utc_now_iso, write_json, write_raw_snapshot


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
) -> dict[str, Any]:
    collector = get_collector(account_ref.platform, client=client)
    run_id = utc_now_iso().replace(":", "-") + "-" + uuid4().hex[:8]
    run_dir = make_run_dir(output_root, collector.platform, account_ref.slug, run_id)

    profile = collector.fetch_account_profile(account_ref)
    request_log = [profile.request_meta]
    write_raw_snapshot(run_dir, category="account", name="profile", payload=profile.raw_payload)

    posts: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    replies: list[dict[str, Any]] = []

    post_cursor = None
    page_index = 0
    while True:
        page_index += 1
        page = collector.fetch_account_posts(account_ref, cursor=post_cursor, page_size=page_size)
        request_log.append(page.request_meta)
        write_raw_snapshot(
            run_dir,
            category="account_posts",
            name=f"page-{page_index:03d}",
            payload=page.raw_payload,
        )
        page_records = page.records
        if max_posts is not None:
            remaining = max_posts - len(posts)
            page_records = page_records[: max(remaining, 0)]
        posts.extend(page_records)
        if max_posts is not None and len(posts) >= max_posts:
            break
        if not page.has_next_page or not page.next_cursor:
            break
        post_cursor = page.next_cursor

    enriched_posts: list[dict[str, Any]] = []
    for post in posts:
        post_ref = PostRef(
            platform=collector.platform,
            media_id=post["post_id"],
            shortcode=post.get("code"),
            url=post.get("url"),
        )
        detail = collector.fetch_post_detail(post_ref)
        request_log.append(detail.request_meta)
        write_raw_snapshot(
            run_dir,
            category="post_detail",
            name=post.get("code") or post["post_id"] or "detail",
            payload=detail.raw_payload,
        )
        enriched_posts.append(_merge_post_records(post, detail.record))
        if include_comments:
            _collect_comments_for_post(
                collector,
                post_ref,
                comments,
                replies,
                request_log,
                run_dir,
                max_comment_pages=max_comment_pages,
            )

    bundle = CollectionBundle(
        run_id=run_id,
        platform=collector.platform,
        account_ref=account_ref.to_params() | {"platform": account_ref.platform},
        collected_at=utc_now_iso(),
        include_comments=include_comments,
        profile=profile.record,
        posts=enriched_posts,
        comments=comments,
        replies=replies,
        request_log=request_log,
    )
    bundle_path = write_json(run_dir / "bundle.json", bundle.to_dict())
    bundle.output_paths = {
        "run_dir": str(run_dir),
        "bundle": str(bundle_path),
        "raw_dir": str(run_dir / "raw"),
    }
    write_json(run_dir / "bundle.json", bundle.to_dict())
    return bundle.to_dict()


def _collect_comments_for_post(
    collector,
    post_ref: PostRef,
    comments: list[dict[str, Any]],
    replies: list[dict[str, Any]],
    request_log: list[dict[str, Any]],
    run_dir: Path,
    *,
    max_comment_pages: int | None,
) -> None:
    cursor = None
    page_index = 0
    while True:
        page_index += 1
        page = collector.fetch_post_comments(post_ref, cursor=cursor)
        request_log.append(page.request_meta)
        write_raw_snapshot(
            run_dir,
            category="comments",
            name=f"{post_ref.slug}-page-{page_index:03d}",
            payload=page.raw_payload,
        )
        comments.extend(page.records)
        for comment in page.records:
            if int(comment.get("child_comment_count") or 0) > 0:
                _collect_replies_for_comment(
                    collector,
                    post_ref,
                    comment["comment_id"],
                    replies,
                    request_log,
                    run_dir,
                    max_comment_pages=max_comment_pages,
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
    run_dir: Path,
    *,
    max_comment_pages: int | None,
) -> None:
    cursor = None
    page_index = 0
    while True:
        page_index += 1
        page = collector.fetch_comment_replies(post_ref, comment_id, cursor=cursor)
        request_log.append(page.request_meta)
        write_raw_snapshot(
            run_dir,
            category="replies",
            name=f"{post_ref.slug}-{comment_id}-page-{page_index:03d}",
            payload=page.raw_payload,
        )
        replies.extend(page.records)
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
