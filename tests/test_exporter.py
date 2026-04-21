from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.collect.exporter import export_dashboard_data, sync_docs_data


class ExporterTest(unittest.TestCase):
    def test_export_dashboard_data_matches_expected_contract_for_item_layout(self) -> None:
        account = {
            "platform": "instagram",
            "account_ref": {"platform": "instagram", "username": "nasa"},
            "extracted_at": "2026-04-19T00:00:00Z",
            "profile": {
                "platform": "instagram",
                "account_id": "u1",
                "username": "nasa",
                "full_name": "NASA",
                "biography": "Space agency",
                "external_url": "https://nasa.gov",
                "profile_pic_url": "https://img/profile.jpg",
                "profile_pic_local_path": "data/collect/instagram/nasa/media/account/profile.jpg",
                "is_verified": True,
                "is_private": False,
                "followers_count": 100,
                "following_count": 10,
                "posts_count": 2,
                "reels_count": 1,
            },
            "metrics": {
                "stored_items": 1,
                "stored_posts": 1,
                "stored_reels": 0,
                "stored_likes": 25,
                "stored_comments": 3,
            },
        }
        item = {
            "platform": "instagram",
            "account_ref": {"platform": "instagram", "username": "nasa"},
            "item_type": "post",
            "item_key": "ABC123",
            "extracted_at": "2026-04-19T00:00:00Z",
            "post": {
                "platform": "instagram",
                "post_id": "p1",
                "code": "ABC123",
                "url": "https://www.instagram.com/p/ABC123/",
                "item_type": "post",
                "caption": "Hello #space",
                "hashtags": ["space"],
                "media_type": "carousel",
                "taken_at": "2026-04-18T12:00:00Z",
                "thumbnail_url": "https://img/post-1.jpg",
                "thumbnail_local_path": "data/collect/instagram/nasa/posts/ABC123/media/image-01.jpg",
                "image_urls": ["https://img/post-1.jpg"],
                "image_local_paths": [
                    "data/collect/instagram/nasa/posts/ABC123/media/image-01.jpg"
                ],
                "video_urls": ["https://video/post-2.mp4"],
                "video_local_paths": [
                    "data/collect/instagram/nasa/posts/ABC123/media/02-video.mp4"
                ],
                "media_local_paths": [
                    "data/collect/instagram/nasa/posts/ABC123/media/image-01.jpg",
                    "data/collect/instagram/nasa/posts/ABC123/media/02-video.mp4",
                ],
                "media_assets": [
                    {
                        "position": 1,
                        "media_type": "image",
                        "url": "https://img/post-1.jpg",
                        "thumbnail_url": "https://img/post-1.jpg",
                        "local_path": "data/collect/instagram/nasa/posts/ABC123/media/image-01.jpg",
                    },
                    {
                        "position": 2,
                        "media_type": "video",
                        "url": "https://video/post-2.mp4",
                        "thumbnail_url": "https://img/post-2.jpg",
                        "local_path": "data/collect/instagram/nasa/posts/ABC123/media/02-video.mp4",
                        "thumbnail_local_path": "data/collect/instagram/nasa/posts/ABC123/media/02-video-thumb.jpg",
                    },
                ],
                "metrics": {"likes": 25, "comments": 3},
                "author": {"account_id": "u1", "username": "nasa"},
            },
            "comments": [{"comment_id": "c1", "platform": "instagram", "post_ref": {"code": "ABC123"}}],
            "replies": [{"comment_id": "r1", "platform": "instagram", "post_ref": {"code": "ABC123"}}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_root = Path(temp_dir) / "collect" / "instagram" / "nasa"
            output_dir = Path(temp_dir) / "dashboard"
            (input_root / "posts" / "ABC123").mkdir(parents=True, exist_ok=True)
            (input_root / "account.json").write_text(json.dumps(account), encoding="utf-8")
            (input_root / "posts" / "ABC123" / "item.json").write_text(
                json.dumps(item),
                encoding="utf-8",
            )

            written = export_dashboard_data(input_root.parent.parent, output_dir=output_dir)

            self.assertEqual(
                sorted(written.keys()),
                [
                    "accounts",
                    "engagement_timeseries",
                    "hashtags",
                    "posts",
                    "site_summary",
                ],
            )
            site_summary = json.loads((output_dir / "site-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(site_summary["counts"]["accounts"], 1)
            self.assertEqual(site_summary["counts"]["posts"], 1)
            self.assertEqual(site_summary["counts"]["comments"], 2)
            accounts = json.loads((output_dir / "accounts.json").read_text(encoding="utf-8"))
            self.assertEqual(accounts[0]["profile_pic_local_path"], account["profile"]["profile_pic_local_path"])
            self.assertEqual(accounts[0]["stored_likes"], 25)
            posts = json.loads((output_dir / "posts.json").read_text(encoding="utf-8"))
            self.assertEqual(posts[0]["thumbnail_local_path"], item["post"]["thumbnail_local_path"])
            self.assertEqual(posts[0]["item_type"], "post")
            self.assertEqual(posts[0]["video_local_paths"], item["post"]["video_local_paths"])
            self.assertEqual(posts[0]["media_assets"][1]["media_type"], "video")
            hashtags = json.loads((output_dir / "hashtags.json").read_text(encoding="utf-8"))
            self.assertEqual(hashtags[0]["hashtag"], "space")

    def test_export_dashboard_data_supports_legacy_bundle_files(self) -> None:
        bundle = {
            "run_id": "run-1",
            "platform": "instagram",
            "account_ref": {"platform": "instagram", "username": "nasa"},
            "collected_at": "2026-04-19T00:00:00Z",
            "include_comments": True,
            "profile": {
                "platform": "instagram",
                "account_id": "u1",
                "username": "nasa",
                "full_name": "NASA",
                "biography": "Space agency",
                "external_url": "https://nasa.gov",
                "profile_pic_url": "https://img/profile.jpg",
                "profile_pic_local_path": "data/collect/instagram/nasa/run-1/media/account/profile.jpg",
                "is_verified": True,
                "is_private": False,
                "followers_count": 100,
                "following_count": 10,
                "posts_count": 2,
                "reels_count": 1,
            },
            "posts": [
                {
                    "platform": "instagram",
                    "post_id": "p1",
                    "code": "ABC123",
                    "url": "https://www.instagram.com/p/ABC123/",
                    "caption": "Hello #space",
                    "hashtags": ["space"],
                    "media_type": "video",
                    "taken_at": "2026-04-18T12:00:00Z",
                    "thumbnail_url": "https://img/post-thumb.jpg",
                    "thumbnail_local_path": "data/collect/instagram/nasa/run-1/media/posts/ABC123/image-01.jpg",
                    "image_urls": [],
                    "image_local_paths": [],
                    "video_urls": ["https://video/post.mp4"],
                    "video_local_paths": [
                        "data/collect/instagram/nasa/run-1/media/posts/ABC123/video-01.mp4"
                    ],
                    "media_local_paths": [
                        "data/collect/instagram/nasa/run-1/media/posts/ABC123/video-01.mp4"
                    ],
                    "metrics": {"likes": 25, "comments": 3},
                    "author": {"account_id": "u1", "username": "nasa"},
                }
            ],
            "comments": [{"comment_id": "c1", "platform": "instagram", "post_ref": {"code": "ABC123"}}],
            "replies": [{"comment_id": "r1", "platform": "instagram", "post_ref": {"code": "ABC123"}}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "bundle.json"
            output_dir = Path(temp_dir) / "dashboard"
            input_path.write_text(json.dumps(bundle), encoding="utf-8")

            export_dashboard_data(input_path, output_dir=output_dir)
            posts = json.loads((output_dir / "posts.json").read_text(encoding="utf-8"))
            self.assertEqual(posts[0]["post_id"], "p1")
            self.assertEqual(posts[0]["video_urls"], ["https://video/post.mp4"])

    def test_sync_docs_data_copies_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "data"
            docs_dir = Path(temp_dir) / "docs"
            sample_payloads = {
                "site-summary.json": {"project_status": "waiting_for_data"},
                "accounts.json": [],
                "posts.json": [],
                "hashtags.json": [],
                "engagement-timeseries.json": [],
            }
            source_dir.mkdir(parents=True, exist_ok=True)
            for filename, payload in sample_payloads.items():
                (source_dir / filename).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            written = sync_docs_data(source_dir=source_dir, docs_dir=docs_dir)

            self.assertEqual(
                sorted(written.keys()),
                [
                    "accounts",
                    "engagement_timeseries",
                    "hashtags",
                    "posts",
                    "site_summary",
                ],
            )
            self.assertEqual(
                json.loads((docs_dir / "site-summary.json").read_text(encoding="utf-8")),
                {"project_status": "waiting_for_data"},
            )


if __name__ == "__main__":
    unittest.main()
