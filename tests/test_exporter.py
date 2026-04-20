from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.collect.exporter import export_dashboard_data, sync_docs_data


class ExporterTest(unittest.TestCase):
    def test_export_dashboard_data_matches_expected_contract(self) -> None:
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
                    "media_type": "image",
                    "taken_at": "2026-04-18T12:00:00Z",
                    "thumbnail_url": "https://img/post.jpg",
                    "metrics": {"likes": 25, "comments": 3},
                    "author": {"account_id": "u1", "username": "nasa"},
                }
            ],
            "comments": [{"comment_id": "c1"}],
            "replies": [{"comment_id": "r1"}],
            "request_log": [],
            "output_paths": {},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "bundle.json"
            output_dir = Path(temp_dir) / "dashboard"
            input_path.write_text(json.dumps(bundle), encoding="utf-8")

            written = export_dashboard_data(input_path, output_dir=output_dir)

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
            hashtags = json.loads((output_dir / "hashtags.json").read_text(encoding="utf-8"))
            self.assertEqual(hashtags[0]["hashtag"], "space")

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
