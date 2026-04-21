from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.collect.client import TikHubClient, TransportResult
from src.collect.exporter import export_dashboard_data
from src.collect.models import AccountRef
from src.collect.service import collect_account_bundle
from src.collect.storage import DownloadedAsset


class CollectServiceIntegrationTest(unittest.TestCase):
    def test_collect_bundle_and_export_dashboard(self) -> None:
        client = TikHubClient(api_key="demo-token", transport=self._transport)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "collect"
            bundle = collect_account_bundle(
                AccountRef(platform="instagram", username="nasa"),
                include_comments=True,
                max_posts=1,
                max_comment_pages=1,
                output_root=output_root,
                client=client,
                media_downloader=self._download_asset,
            )

            account_path = Path(bundle["output_paths"]["account"])
            item_path = Path(bundle["output_paths"]["items"][0])
            self.assertTrue(account_path.exists())
            self.assertTrue(item_path.exists())
            self.assertEqual(len(bundle["posts"]), 1)
            self.assertEqual(len(bundle["comments"]), 1)
            self.assertEqual(len(bundle["replies"]), 1)
            self.assertTrue(Path(bundle["profile"]["profile_pic_local_path"]).exists())
            self.assertTrue(Path(bundle["posts"][0]["thumbnail_local_path"]).exists())
            self.assertEqual(len(bundle["posts"][0]["image_local_paths"]), 1)
            self.assertEqual(len(bundle["posts"][0]["video_local_paths"]), 1)
            self.assertEqual(len(bundle["posts"][0]["media_local_paths"]), 2)
            self.assertEqual(len(bundle["posts"][0]["media_assets"]), 2)
            self.assertTrue(Path(bundle["posts"][0]["image_local_paths"][0]).exists())
            self.assertTrue(Path(bundle["posts"][0]["video_local_paths"][0]).exists())

            dashboard_dir = Path(temp_dir) / "dashboard"
            export_dashboard_data(output_root, output_dir=dashboard_dir)

            posts = json.loads((dashboard_dir / "posts.json").read_text(encoding="utf-8"))
            self.assertEqual(posts[0]["code"], "ABC123")
            self.assertEqual(posts[0]["thumbnail_local_path"], bundle["posts"][0]["thumbnail_local_path"])
            self.assertEqual(posts[0]["video_local_paths"], bundle["posts"][0]["video_local_paths"])
            summary = json.loads((dashboard_dir / "site-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["counts"]["posts"], 1)
            self.assertEqual(summary["project_status"], "ready_with_data")
            account = json.loads(account_path.read_text(encoding="utf-8"))
            self.assertEqual(account["metrics"]["stored_items"], 1)

    def test_collect_bundle_downloads_reel_video_media(self) -> None:
        client = TikHubClient(api_key="demo-token", transport=self._reel_transport)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "collect"
            bundle = collect_account_bundle(
                AccountRef(platform="instagram", username="nasa"),
                include_comments=False,
                max_posts=1,
                output_root=output_root,
                client=client,
                media_downloader=self._download_asset,
            )

            item_path = Path(bundle["output_paths"]["items"][0])
            self.assertEqual(item_path.parent.parent.name, "reels")
            self.assertEqual(bundle["posts"][0]["item_type"], "reel")
            self.assertEqual(bundle["posts"][0]["metrics"]["plays"], 456)
            self.assertEqual(len(bundle["posts"][0]["video_local_paths"]), 1)
            self.assertTrue(Path(bundle["posts"][0]["video_local_paths"][0]).exists())
            self.assertTrue(Path(bundle["posts"][0]["thumbnail_local_path"]).exists())

    def test_collect_bundle_uses_resolved_account_reference_for_posts(self) -> None:
        client = TikHubClient(api_key="demo-token", transport=self._fallback_transport)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "collect"
            bundle = collect_account_bundle(
                AccountRef(platform="instagram", username="baddiewinnkle"),
                include_comments=False,
                max_posts=1,
                output_root=output_root,
                client=client,
                media_downloader=self._download_asset,
            )

            self.assertEqual(bundle["profile"]["username"], "baddiewinkle")
            self.assertEqual(bundle["posts"][0]["author"]["username"], "baddiewinkle")
            self.assertEqual(
                bundle["request_log"][0]["resolved_account"],
                {"username": "baddiewinkle", "user_id": "1255252836"},
            )
            self.assertEqual(Path(bundle["output_paths"]["account"]).parent.name, "baddiewinkle")

    def _download_asset(self, url, output_dir, *, stem):
        output_dir.mkdir(parents=True, exist_ok=True)
        if "video/" in url:
            suffix = ".mp4"
            content_type = "video/mp4"
        elif "img/" in url:
            suffix = ".jpg"
            content_type = "image/jpeg"
        else:
            suffix = ".bin"
            content_type = "application/octet-stream"
        path = output_dir / f"{stem}{suffix}"
        path.write_bytes(b"fake-media")
        return DownloadedAsset(
            source_url=url,
            content_type=content_type,
            size_bytes=len(b"fake-media"),
            path=path,
        )

    def _transport(self, method, url, headers, timeout):
        parsed = urlparse(url)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path.endswith("/get_user_profile"):
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
                            "profile_pic_url_hd": "https://img/profile-hd.jpg",
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

        if path.endswith("/get_user_posts"):
            self.assertEqual(params["username"][0], "nasa")
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
                                    "caption": {"text": "Hello #space"},
                                    "taken_at": 1713489600,
                                    "like_count": 25,
                                    "comment_count": 3,
                                    "media_type": 8,
                                    "display_url": "https://img/carousel-cover.jpg",
                                    "user": {
                                        "id": "u1",
                                        "username": "nasa",
                                        "full_name": "NASA",
                                        "is_verified": True,
                                    },
                                }
                            }
                        ],
                        "page_info": {"has_next_page": False, "end_cursor": None},
                    },
                },
            )

        if path.endswith("/get_post_info"):
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "detail-1",
                    "data": {
                        "items": [
                            {
                                "id": "p1",
                                "code": "ABC123",
                                "caption": {"text": "Hello #space"},
                                "taken_at": 1713489600,
                                "like_count": 25,
                                "comment_count": 3,
                                "media_type": 8,
                                "image_versions2": {
                                    "candidates": [{"url": "https://img/carousel-cover.jpg"}]
                                },
                                "carousel_media": [
                                    {
                                        "id": "p1-1",
                                        "media_type": 1,
                                        "image_versions2": {
                                            "candidates": [{"url": "https://img/post-1.jpg"}]
                                        },
                                    },
                                    {
                                        "id": "p1-2",
                                        "media_type": 2,
                                        "image_versions2": {
                                            "candidates": [{"url": "https://img/post-2.jpg"}]
                                        },
                                        "video_versions": [
                                            {"url": "https://video/post-2.mp4"},
                                            {"url": "https://video/post-2-low.mp4"},
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
                                "created_at": 1713489700,
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
                        "next_min_id": None,
                    },
                },
            )

        if path.endswith("/get_comment_replies"):
            self.assertEqual(params["comment_id"][0], "c1")
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
                                "created_at": 1713489800,
                                "comment_like_count": 1,
                                "user": {
                                    "pk": "u1",
                                    "username": "nasa",
                                    "full_name": "NASA",
                                    "is_verified": True,
                                },
                            }
                        ],
                        "next_min_child_cursor": None,
                        "has_more_tail_child_comments": False,
                    },
                },
            )

        raise AssertionError(f"Unexpected path: {path}")

    def _reel_transport(self, method, url, headers, timeout):
        parsed = urlparse(url)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path.endswith("/get_user_profile"):
            return self._transport(method, url, headers, timeout)

        if path.endswith("/get_user_posts"):
            self.assertEqual(params["username"][0], "nasa")
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "posts-reel-1",
                    "data": {
                        "edges": [
                            {
                                "node": {
                                    "id": "r1",
                                    "code": "REEL123",
                                    "caption": {"text": "Hello reel #space"},
                                    "taken_at": 1713489600,
                                    "like_count": 99,
                                    "comment_count": 12,
                                    "play_count": 456,
                                    "media_type": 2,
                                    "product_type": "clips",
                                    "display_url": "https://img/reel-thumb.jpg",
                                    "user": {
                                        "id": "u1",
                                        "username": "nasa",
                                        "full_name": "NASA",
                                        "is_verified": True,
                                    },
                                }
                            }
                        ],
                        "page_info": {"has_next_page": False, "end_cursor": None},
                    },
                },
            )

        if path.endswith("/get_post_info"):
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "detail-reel-1",
                    "data": {
                        "items": [
                            {
                                "id": "r1",
                                "code": "REEL123",
                                "caption": {"text": "Hello reel #space"},
                                "taken_at": 1713489600,
                                "like_count": 99,
                                "comment_count": 12,
                                "play_count": 456,
                                "media_type": 2,
                                "product_type": "clips",
                                "image_versions2": {
                                    "candidates": [{"url": "https://img/reel-thumb.jpg"}]
                                },
                                "video_versions": [
                                    {"url": "https://video/reel-main.mp4"},
                                    {"url": "https://video/reel-low.mp4"},
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

        raise AssertionError(f"Unexpected path: {path}")

    def _fallback_transport(self, method, url, headers, timeout):
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
            self.assertEqual(params["user_id"][0], "1255252836")
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "profile-1",
                    "data": {
                        "user": {
                            "id": "1255252836",
                            "username": "baddiewinkle",
                            "full_name": "Helen Van Winkle",
                            "biography": "Grandma influencer",
                            "external_url": None,
                            "profile_pic_url_hd": "https://img/profile-hd.jpg",
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
                                    "profile_pic_url": "https://img/profile.jpg",
                                },
                            }
                        ]
                    },
                },
            )

        if path.endswith("/get_user_posts"):
            self.assertEqual(params["username"][0], "baddiewinkle")
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
                                    "caption": {"text": "Hello #space"},
                                    "taken_at": 1713489600,
                                    "like_count": 25,
                                    "comment_count": 3,
                                    "media_type": 1,
                                    "display_url": "https://img/post.jpg",
                                    "user": {
                                        "id": "1255252836",
                                        "username": "baddiewinkle",
                                        "full_name": "Helen Van Winkle",
                                        "is_verified": True,
                                    },
                                }
                            }
                        ],
                        "page_info": {"has_next_page": False, "end_cursor": None},
                    },
                },
            )

        if path.endswith("/get_post_info"):
            return TransportResult(
                status_code=200,
                payload={
                    "time": "2026-04-19T00:00:00Z",
                    "request_id": "detail-1",
                    "data": {
                        "items": [
                            {
                                "id": "p1",
                                "code": "ABC123",
                                "caption": {"text": "Hello #space"},
                                "taken_at": 1713489600,
                                "like_count": 25,
                                "comment_count": 3,
                                "media_type": 1,
                                "image_versions2": {"candidates": [{"url": "https://img/post.jpg"}]},
                                "user": {
                                    "id": "1255252836",
                                    "username": "baddiewinkle",
                                    "full_name": "Helen Van Winkle",
                                    "is_verified": True,
                                },
                            }
                        ]
                    },
                },
            )

        raise AssertionError(f"Unexpected path: {path}")


if __name__ == "__main__":
    unittest.main()
