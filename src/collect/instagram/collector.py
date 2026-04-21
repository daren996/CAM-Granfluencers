from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from ..base import BaseCollector
from ..client import TikHubClient
from ..exceptions import TikHubError
from ..models import AccountRef, Cursor, PageEnvelope, PostRef, RecordEnvelope
from ..normalization import (
    extract_hashtags,
    first_image_url,
    image_urls,
    media_assets,
    media_type_name,
    timestamp_to_iso8601,
    video_urls,
)


class InstagramCollector(BaseCollector):
    """Instagram collector built on TikHub's Instagram V3 APIs."""

    platform = "instagram"

    def __init__(self, client: TikHubClient) -> None:
        self.client = client

    def fetch_account_profile(self, account_ref: AccountRef) -> RecordEnvelope:
        try:
            payload, meta = self.client.get(
                "/api/v1/instagram/v3/get_user_profile", account_ref.to_params()
            )
        except TikHubError as exc:
            fallback = self._retry_profile_lookup_with_search(account_ref, exc)
            if fallback is None:
                raise
            payload, meta = fallback

        user = (payload.get("data") or {}).get("user") or {}
        return RecordEnvelope(
            record=self._normalize_profile(user, meta),
            raw_payload=payload,
            request_meta=meta,
        )

    def fetch_account_posts(
        self, account_ref: AccountRef, cursor: Cursor = None, page_size: int | None = None
    ) -> PageEnvelope:
        params = account_ref.to_params()
        if page_size is not None:
            params["first"] = page_size
        if cursor:
            params["after"] = cursor
        payload, meta = self.client.get("/api/v1/instagram/v3/get_user_posts", params)
        data = payload.get("data") or {}
        page_info = data.get("page_info") or {}
        records = [
            self._normalize_post(node=edge.get("node") or {}, request_meta=meta)
            for edge in data.get("edges", []) or []
        ]
        return PageEnvelope(
            records=records,
            raw_payload=payload,
            request_meta={
                **meta,
                "cursor_in": cursor,
                "cursor_out": page_info.get("end_cursor"),
            },
            next_cursor=page_info.get("end_cursor"),
            has_next_page=bool(page_info.get("has_next_page")),
        )

    def fetch_post_detail(self, post_ref: PostRef) -> RecordEnvelope:
        params = post_ref.to_params()
        if post_ref.shortcode and not post_ref.media_id and not post_ref.url:
            path = "/api/v1/instagram/v3/get_post_info_by_code"
        else:
            path = "/api/v1/instagram/v3/get_post_info"
        payload, meta = self.client.get(path, params)
        items = (payload.get("data") or {}).get("items") or []
        item = items[0] if items else {}
        return RecordEnvelope(
            record=self._normalize_post(item, meta),
            raw_payload=payload,
            request_meta=meta,
        )

    def fetch_post_comments(
        self, post_ref: PostRef, cursor: Cursor = None, sort: str = "popular"
    ) -> PageEnvelope:
        params = post_ref.to_params()
        params["sort_order"] = sort
        if cursor:
            params["min_id"] = cursor
        payload, meta = self.client.get("/api/v1/instagram/v3/get_post_comments", params)
        data = payload.get("data") or {}
        comments = data.get("comments") or []
        next_cursor = data.get("next_min_id")
        return PageEnvelope(
            records=[
                self._normalize_comment(comment, meta, post_ref=post_ref) for comment in comments
            ],
            raw_payload=payload,
            request_meta={**meta, "cursor_in": cursor, "cursor_out": next_cursor},
            next_cursor=next_cursor,
            has_next_page=bool(next_cursor),
        )

    def fetch_comment_replies(
        self, post_ref: PostRef, comment_id: str, cursor: Cursor = None
    ) -> PageEnvelope:
        params = post_ref.to_params()
        params["comment_id"] = comment_id
        if cursor:
            params["min_id"] = cursor
        payload, meta = self.client.get("/api/v1/instagram/v3/get_comment_replies", params)
        data = payload.get("data") or {}
        next_cursor = data.get("next_min_child_cursor")
        replies = data.get("child_comments") or []
        return PageEnvelope(
            records=[
                self._normalize_comment(
                    reply, meta, post_ref=post_ref, parent_comment_id=comment_id
                )
                for reply in replies
            ],
            raw_payload=payload,
            request_meta={**meta, "cursor_in": cursor, "cursor_out": next_cursor},
            next_cursor=next_cursor,
            has_next_page=bool(data.get("has_more_tail_child_comments") or next_cursor),
        )

    def search_accounts(self, query: str) -> PageEnvelope:
        payload, meta = self.client.get("/api/v1/instagram/v3/search_users", {"query": query})
        data = payload.get("data") or {}
        users = data.get("users") or []
        return PageEnvelope(
            records=[self._normalize_search_result(user, meta) for user in users],
            raw_payload=payload,
            request_meta=meta,
            next_cursor=None,
            has_next_page=False,
        )

    def _normalize_profile(self, user: dict[str, Any], request_meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "account_id": self._stringify(user.get("id")),
            "username": user.get("username"),
            "full_name": user.get("full_name"),
            "biography": user.get("biography"),
            "external_url": user.get("external_url"),
            "profile_pic_url": user.get("profile_pic_url_hd") or user.get("profile_pic_url"),
            "is_verified": bool(user.get("is_verified")),
            "is_private": bool(user.get("is_private")),
            "followers_count": self._nested_count(user, "edge_followed_by"),
            "following_count": self._nested_count(user, "edge_follow"),
            "posts_count": self._nested_count(user, "edge_owner_to_timeline_media"),
            "reels_count": self._nested_count(user, "edge_felix_video_timeline"),
            "raw_ids": {"user_id": self._stringify(user.get("id"))},
            "request_meta": request_meta,
        }

    def _normalize_post(self, node: dict[str, Any], request_meta: dict[str, Any]) -> dict[str, Any]:
        caption = self._extract_caption(node)
        code = node.get("code")
        author = node.get("user") or {}
        item_type = self._item_type(node)
        return {
            "platform": self.platform,
            "post_id": self._stringify(node.get("id")),
            "code": code,
            "url": self._post_url(code, item_type),
            "item_type": item_type,
            "caption": caption,
            "hashtags": extract_hashtags(caption),
            "media_type": media_type_name(node.get("media_type")),
            "taken_at": timestamp_to_iso8601(node.get("taken_at")),
            "thumbnail_url": first_image_url(node),
            "image_urls": image_urls(node),
            "video_urls": video_urls(node),
            "media_assets": media_assets(node),
            "metrics": {
                "likes": node.get("like_count"),
                "comments": node.get("comment_count"),
            },
            "author": {
                "account_id": self._stringify(author.get("id")),
                "username": author.get("username"),
                "full_name": author.get("full_name"),
                "is_verified": bool(author.get("is_verified")) if author else None,
            },
            "raw_ids": {
                "post_id": self._stringify(node.get("id")),
                "code": code,
                "media_type": node.get("media_type"),
                "product_type": node.get("product_type"),
            },
            "request_meta": request_meta,
        }

    def _normalize_comment(
        self,
        comment: dict[str, Any],
        request_meta: dict[str, Any],
        *,
        post_ref: PostRef,
        parent_comment_id: str | None = None,
    ) -> dict[str, Any]:
        user = comment.get("user") or {}
        return {
            "platform": self.platform,
            "post_ref": post_ref.to_params(),
            "comment_id": self._stringify(comment.get("pk") or comment.get("comment_id")),
            "parent_comment_id": parent_comment_id,
            "text": comment.get("text"),
            "created_at": timestamp_to_iso8601(comment.get("created_at")),
            "like_count": comment.get("comment_like_count"),
            "child_comment_count": comment.get("child_comment_count"),
            "user": {
                "account_id": self._stringify(user.get("pk") or user.get("id")),
                "username": user.get("username"),
                "full_name": user.get("full_name"),
                "is_verified": bool(user.get("is_verified")) if user else None,
            },
            "raw_ids": {
                "comment_id": self._stringify(comment.get("pk") or comment.get("comment_id")),
                "post_code": post_ref.shortcode,
                "post_media_id": post_ref.media_id,
            },
            "request_meta": request_meta,
        }

    def _normalize_search_result(
        self, user: dict[str, Any], request_meta: dict[str, Any]
    ) -> dict[str, Any]:
        user_data = user.get("user") or user
        return {
            "platform": self.platform,
            "account_id": self._stringify(user_data.get("pk") or user_data.get("id")),
            "username": user_data.get("username"),
            "full_name": user_data.get("full_name"),
            "is_verified": bool(user_data.get("is_verified")),
            "profile_pic_url": user_data.get("profile_pic_url"),
            "request_meta": request_meta,
        }

    def _extract_caption(self, node: dict[str, Any]) -> str | None:
        caption = node.get("caption")
        if isinstance(caption, dict):
            return caption.get("text")
        if isinstance(caption, str):
            return caption
        edge_caption = ((node.get("edge_media_to_caption") or {}).get("edges") or [])
        if edge_caption:
            return ((edge_caption[0].get("node") or {}).get("text"))
        return None

    def _nested_count(self, node: dict[str, Any], key: str) -> int | None:
        nested = node.get(key) or {}
        count = nested.get("count")
        if count is None:
            return None
        return int(count)

    def _post_url(self, code: str | None, item_type: str = "post") -> str | None:
        if not code:
            return None
        if item_type == "reel":
            return f"https://www.instagram.com/reel/{code}/"
        return f"https://www.instagram.com/p/{code}/"

    def _item_type(self, node: dict[str, Any]) -> str:
        product_type = str(node.get("product_type") or "").lower()
        if product_type in {"clips", "igtv", "reels"}:
            return "reel"
        if media_type_name(node.get("media_type")) == "video":
            return "reel"
        return "post"

    def _stringify(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    def _retry_profile_lookup_with_search(
        self, account_ref: AccountRef, original_error: TikHubError
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        if original_error.status_code != 400 or not account_ref.username:
            return None

        try:
            search_payload, search_meta = self.client.get(
                "/api/v1/instagram/v3/search_users", {"query": account_ref.username}
            )
        except TikHubError:
            return None

        candidates = (search_payload.get("data") or {}).get("users") or []
        for candidate in self._rank_search_candidates(account_ref.username, candidates):
            candidate_user = candidate.get("user") or candidate
            candidate_id = self._stringify(candidate_user.get("pk") or candidate_user.get("id"))
            candidate_username = candidate_user.get("username")
            if not candidate_id and not candidate_username:
                continue

            params: dict[str, Any]
            if candidate_id:
                params = {"user_id": candidate_id}
            else:
                params = {"username": candidate_username}

            try:
                payload, meta = self.client.get("/api/v1/instagram/v3/get_user_profile", params)
            except TikHubError:
                continue

            return payload, {
                **meta,
                "fallback_from": account_ref.to_params(),
                "failed_profile_lookup": {
                    "error": str(original_error),
                    "status_code": original_error.status_code,
                    "url": original_error.url,
                    "payload": original_error.payload,
                },
                "search_meta": search_meta,
                "resolved_account": {
                    "username": candidate_username,
                    "user_id": candidate_id,
                },
            }

        return None

    def _rank_search_candidates(
        self, requested_username: str, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        target = requested_username.casefold()
        target_alnum = self._alnum_key(requested_username)

        def score(candidate: dict[str, Any]) -> tuple[int, int, float, int]:
            user_data = candidate.get("user") or candidate
            username = str(user_data.get("username") or "")
            username_key = username.casefold()
            username_alnum = self._alnum_key(username)

            exact_match = 1 if username_key == target else 0
            normalized_match = 1 if target_alnum and username_alnum == target_alnum else 0
            similarity = SequenceMatcher(None, target, username_key).ratio()
            position = int(candidate.get("position") or 0)
            return (exact_match, normalized_match, similarity, -position)

        return sorted(candidates, key=score, reverse=True)

    def _alnum_key(self, value: str) -> str:
        return "".join(ch for ch in value.casefold() if ch.isalnum())
