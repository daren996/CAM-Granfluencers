from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlparse

from src.collect.client import TikHubClient, TransportResult
from src.collect.instagram import InstagramCollector
from src.collect.models import AccountRef, PostRef


class InstagramCollectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TikHubClient(api_key="demo-token", transport=self._transport)
        self.collector = InstagramCollector(self.client)

    def test_fetch_account_posts_preserves_cursor(self) -> None:
        page = self.collector.fetch_account_posts(
            AccountRef(platform="instagram", username="nasa"),
            cursor="cursor-1",
            page_size=12,
        )

        self.assertEqual(page.next_cursor, "cursor-2")
        self.assertTrue(page.has_next_page)
        self.assertEqual(page.request_meta["cursor_in"], "cursor-1")
        self.assertEqual(page.request_meta["cursor_out"], "cursor-2")
        self.assertEqual(page.records[0]["hashtags"], ["space"])
        self.assertEqual(page.records[0]["image_urls"], ["https://img/post.jpg"])
        self.assertEqual(page.records[0]["video_urls"], [])
        self.assertEqual(
            page.records[0]["media_assets"],
            [
                {
                    "position": 1,
                    "media_type": "image",
                    "url": "https://img/post.jpg",
                    "thumbnail_url": "https://img/post.jpg",
                }
            ],
        )

    def test_fetch_post_detail_collects_carousel_images_and_videos(self) -> None:
        record = self.collector.fetch_post_detail(
            PostRef(platform="instagram", shortcode="CAR123")
        )

        self.assertEqual(record.record["image_urls"], ["https://img/carousel-1.jpg"])
        self.assertEqual(record.record["video_urls"], ["https://video/carousel-2.mp4"])
        self.assertEqual(
            record.record["media_assets"],
            [
                {
                    "position": 1,
                    "media_type": "image",
                    "url": "https://img/carousel-1.jpg",
                    "thumbnail_url": "https://img/carousel-1.jpg",
                },
                {
                    "position": 2,
                    "media_type": "video",
                    "url": "https://video/carousel-2.mp4",
                    "thumbnail_url": "https://img/carousel-2.jpg",
                },
            ],
        )

    def test_fetch_post_comments_preserves_cursor(self) -> None:
        page = self.collector.fetch_post_comments(
            PostRef(platform="instagram", shortcode="ABC123"),
            cursor="comment-cursor",
            sort="newest",
        )

        self.assertEqual(page.next_cursor, "comment-next")
        self.assertTrue(page.has_next_page)
        self.assertEqual(page.request_meta["cursor_in"], "comment-cursor")
        self.assertEqual(page.records[0]["comment_id"], "c1")

    def test_fetch_comment_replies_preserves_cursor(self) -> None:
        page = self.collector.fetch_comment_replies(
            PostRef(platform="instagram", shortcode="ABC123"),
            comment_id="c1",
            cursor="reply-cursor",
        )

        self.assertEqual(page.next_cursor, "reply-next")
        self.assertTrue(page.has_next_page)
        self.assertEqual(page.request_meta["cursor_in"], "reply-cursor")
        self.assertEqual(page.records[0]["parent_comment_id"], "c1")

    def test_fetch_profile_normalizes_expected_fields(self) -> None:
        record = self.collector.fetch_account_profile(
            AccountRef(platform="instagram", username="nasa")
        )

        self.assertEqual(record.record["username"], "nasa")
        self.assertEqual(record.record["followers_count"], 100)
        self.assertEqual(
            record.record["request_meta"]["source_endpoint"],
            "/api/v1/instagram/v3/get_user_profile",
        )

    def test_fetch_profile_falls_back_to_search_when_username_lookup_breaks(self) -> None:
        record = self.collector.fetch_account_profile(
            AccountRef(platform="instagram", username="baddiewinnkle")
        )

        self.assertEqual(record.record["username"], "baddiewinkle")
        self.assertEqual(record.record["account_id"], "1255252836")
        self.assertEqual(
            record.record["request_meta"]["fallback_from"],
            {"username": "baddiewinnkle"},
        )
        self.assertEqual(
            record.record["request_meta"]["resolved_account"],
            {"username": "baddiewinkle", "user_id": "1255252836"},
        )
        self.assertEqual(
            record.record["request_meta"]["search_meta"]["source_endpoint"],
            "/api/v1/instagram/v3/search_users",
        )

    def _transport(self, method, url, headers, timeout):
        parsed = urlparse(url)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path.endswith("/get_user_profile"):
            if params.get("username") == ["baddiewinnkle"]:
                return TransportResult(
                    status_code=200,
                    payload={
                        "request_id": "profile-fail-1",
                        "router": "/api/v1/instagram/v3/get_user_profile",
                        "docs": "https://api.tikhub.io/#/Instagram-V3-API/get_user_profile_api_v1_instagram_v3_get",
                        "data": {
                            "code": 400,
                            "message": "execution error",
                            "data": None,
                        },
                    },
                )
            if params.get("user_id") == ["1255252836"] or params.get("username") == ["baddiewinkle"]:
                return TransportResult(
                    status_code=200,
                    payload={
                        "time": "2026-04-19T00:00:00Z",
                        "request_id": "profile-2",
                        "data": {
                            "user": {
                                "id": "1255252836",
                                "username": "baddiewinkle",
                                "full_name": "Helen Van Winkle",
                                "biography": "Grandma influencer",
                                "external_url": None,
                                "profile_pic_url": "https://img/baddie.jpg",
                                "is_verified": True,
                                "is_private": False,
                                "edge_followed_by": {"count": 1000},
                                "edge_follow": {"count": 50},
                                "edge_owner_to_timeline_media": {"count": 10},
                                "edge_felix_video_timeline": {"count": 0},
                            }
                        },
                    },
                )
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "profile-1",
                    "data": {
                        "user": {
                            "id": "u1",
                            "username": "nasa",
                            "full_name": "NASA",
                            "biography": "Space agency",
                            "external_url": "https://nasa.gov",
                            "profile_pic_url": "https://img/profile.jpg",
                            "is_verified": True,
                            "is_private": False,
                            "edge_followed_by": {"count": 100},
                            "edge_follow": {"count": 10},
                            "edge_owner_to_timeline_media": {"count": 2},
                            "edge_felix_video_timeline": {"count": 1},
                        }
                    },
                },
            )

        if path.endswith("/search_users"):
            self.assertEqual(params["query"][0], "baddiewinnkle")
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "search-1",
                    "data": {
                        "users": [
                            {
                                "position": 0,
                                "user": {
                                    "pk": "1255252836",
                                    "id": "1255252836",
                                    "username": "baddiewinkle",
                                    "full_name": "Helen Van Winkle",
                                    "is_verified": True,
                                    "profile_pic_url": "https://img/baddie.jpg",
                                },
                            }
                        ]
                    },
                },
            )

        if path.endswith("/get_user_posts"):
            self.assertEqual(params["after"][0], "cursor-1")
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "posts-1",
                    "data": {
                        "edges": [
                            {
                                "node": {
                                    "id": "p1",
                                    "code": "ABC123",
                                    "caption": {"text": "Hello #Space"},
                                    "taken_at": 1713489600,
                                    "like_count": 25,
                                    "comment_count": 3,
                                    "media_type": 1,
                                    "display_url": "https://img/post.jpg",
                                    "user": {
                                        "id": "u1",
                                        "username": "nasa",
                                        "full_name": "NASA",
                                        "is_verified": True,
                                    },
                                }
                            }
                        ],
                        "page_info": {"has_next_page": True, "end_cursor": "cursor-2"},
                    },
                },
            )

        if path.endswith("/get_post_info_by_code"):
            self.assertEqual(params["code"][0], "CAR123")
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "detail-carousel-1",
                    "data": {
                        "items": [
                            {
                                "id": "p2",
                                "code": "CAR123",
                                "caption": {"text": "Carousel #Space"},
                                "taken_at": 1713489600,
                                "like_count": 10,
                                "comment_count": 1,
                                "media_type": 8,
                                "carousel_media": [
                                    {
                                        "id": "p2-1",
                                        "media_type": 1,
                                        "image_versions2": {
                                            "candidates": [{"url": "https://img/carousel-1.jpg"}]
                                        },
                                    },
                                    {
                                        "id": "p2-2",
                                        "media_type": 2,
                                        "image_versions2": {
                                            "candidates": [{"url": "https://img/carousel-2.jpg"}]
                                        },
                                        "video_versions": [
                                            {"url": "https://video/carousel-2.mp4"},
                                            {"url": "https://video/carousel-2-low.mp4"},
                                        ],
                                    },
                                ],
                                "user": {
                                    "id": "u1",
                                    "username": "nasa",
                                    "full_name": "NASA",
                                    "is_verified": True,
                                },
                            }
                        ]
                    },
                },
            )

        if path.endswith("/get_post_comments"):
            self.assertEqual(params["min_id"][0], "comment-cursor")
            self.assertEqual(params["sort_order"][0], "newest")
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "comments-1",
                    "data": {
                        "comments": [
                            {
                                "pk": "c1",
                                "text": "Great post",
                                "created_at": 1713489600,
                                "comment_like_count": 5,
                                "child_comment_count": 1,
                                "user": {
                                    "pk": "u2",
                                    "username": "fan",
                                    "full_name": "Fan One",
                                    "is_verified": False,
                                },
                            }
                        ],
                        "next_min_id": "comment-next",
                    },
                },
            )

        if path.endswith("/get_comment_replies"):
            self.assertEqual(params["comment_id"][0], "c1")
            self.assertEqual(params["min_id"][0], "reply-cursor")
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "replies-1",
                    "data": {
                        "child_comments": [
                            {
                                "pk": "r1",
                                "text": "Reply",
                                "created_at": 1713489600,
                                "comment_like_count": 1,
                                "user": {
                                    "pk": "u3",
                                    "username": "creator",
                                    "full_name": "Creator",
                                    "is_verified": False,
                                },
                            }
                        ],
                        "next_min_child_cursor": "reply-next",
                        "has_more_tail_child_comments": True,
                    },
                },
            )

        raise AssertionError(f"Unexpected path: {path}")


if __name__ == "__main__":
    unittest.main()
