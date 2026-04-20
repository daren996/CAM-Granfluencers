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
            )

            bundle_path = Path(bundle["output_paths"]["bundle"])
            self.assertTrue(bundle_path.exists())
            self.assertEqual(len(bundle["posts"]), 1)
            self.assertEqual(len(bundle["comments"]), 1)
            self.assertEqual(len(bundle["replies"]), 1)

            dashboard_dir = Path(temp_dir) / "dashboard"
            export_dashboard_data(bundle_path, output_dir=dashboard_dir)

            posts = json.loads((dashboard_dir / "posts.json").read_text(encoding="utf-8"))
            self.assertEqual(posts[0]["code"], "ABC123")
            summary = json.loads((dashboard_dir / "site-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["counts"]["posts"], 1)
            self.assertEqual(summary["project_status"], "ready_with_data")

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


if __name__ == "__main__":
    unittest.main()
