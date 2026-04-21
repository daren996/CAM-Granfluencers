from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.collect.cleanup import clear_results
from src.collect.exporter import export_dashboard_data, sync_docs_data


def _make_account_tree(
    *,
    platform: str,
    username: str,
    account_id: str,
    extracted_at: str,
    output_root: Path,
) -> Path:
    account_dir = output_root / platform / username
    item_dir = account_dir / "posts" / f"{username.upper()}1"
    item_dir.mkdir(parents=True, exist_ok=True)
    account = {
        "platform": platform,
        "account_ref": {
            "platform": platform,
            "username": username,
            "user_id": account_id,
        },
        "extracted_at": extracted_at,
        "profile": {
            "platform": platform,
            "account_id": account_id,
            "username": username,
            "full_name": username.upper(),
            "biography": "",
            "external_url": None,
            "profile_pic_url": None,
            "is_verified": False,
            "is_private": False,
            "followers_count": 10,
            "following_count": 1,
            "posts_count": 1,
            "reels_count": 0,
        },
        "metrics": {
            "stored_items": 1,
            "stored_posts": 1,
            "stored_reels": 0,
            "stored_likes": 2,
            "stored_comments": 1,
        },
    }
    item = {
        "platform": platform,
        "account_ref": {
            "platform": platform,
            "username": username,
            "user_id": account_id,
        },
        "item_type": "post",
        "item_key": f"{username.upper()}1",
        "extracted_at": extracted_at,
        "post": {
            "platform": platform,
            "post_id": f"{account_id}-post-1",
            "code": f"{username.upper()}1",
            "url": f"https://www.instagram.com/p/{username.upper()}1/",
            "item_type": "post",
            "caption": f"hello from {username}",
            "hashtags": [username],
            "media_type": "image",
            "taken_at": "2026-04-18T12:00:00Z",
            "thumbnail_url": None,
            "metrics": {"likes": 2, "comments": 1},
            "author": {"account_id": account_id, "username": username},
        },
        "comments": [],
        "replies": [],
    }
    account_path = account_dir / "account.json"
    account_path.write_text(json.dumps(account, ensure_ascii=True, indent=2), encoding="utf-8")
    (item_dir / "item.json").write_text(json.dumps(item, ensure_ascii=True, indent=2), encoding="utf-8")
    return account_path


class ClearResultsTest(unittest.TestCase):
    def test_clear_results_removes_matching_account_tree_and_rebuilds_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            collect_root = root / "collect"
            dashboard_dir = root / "dashboard"
            docs_dir = root / "docs-data"

            nasa_account = _make_account_tree(
                platform="instagram",
                username="nasa",
                account_id="u1",
                extracted_at="2026-04-19T00:00:00Z",
                output_root=collect_root,
            )
            _make_account_tree(
                platform="instagram",
                username="jpl",
                account_id="u2",
                extracted_at="2026-04-20T00:00:00Z",
                output_root=collect_root,
            )

            export_dashboard_data(collect_root, output_dir=dashboard_dir)
            sync_docs_data(source_dir=dashboard_dir, docs_dir=docs_dir)

            result = clear_results(
                platform="instagram",
                username="nasa",
                collect_root=collect_root,
                dashboard_dir=dashboard_dir,
                docs_dir=docs_dir,
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["matched_entries"], 1)
            self.assertEqual(result["checks"]["before"]["data_collect"]["matching_entries"], 1)
            self.assertEqual(result["checks"]["after"]["data_collect"]["matching_entries"], 0)
            self.assertEqual(
                result["checks"]["before"]["data_dashboard"]["matching_accounts"],
                1,
            )
            self.assertEqual(
                result["checks"]["after"]["data_dashboard"]["matching_accounts"],
                0,
            )
            self.assertFalse(nasa_account.exists())

            accounts = json.loads((dashboard_dir / "accounts.json").read_text(encoding="utf-8"))
            posts = json.loads((docs_dir / "posts.json").read_text(encoding="utf-8"))
            self.assertEqual([item["username"] for item in accounts], ["jpl"])
            self.assertEqual([item["username"] for item in posts], ["jpl"])

    def test_clear_results_requires_identifier_without_platform_wipe_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaisesRegex(ValueError, "Provide username, user_id, account_id, or run_id"):
                clear_results(
                    platform="instagram",
                    collect_root=root / "collect",
                    dashboard_dir=root / "dashboard",
                    docs_dir=root / "docs-data",
                )


if __name__ == "__main__":
    unittest.main()
