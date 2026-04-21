from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer

from src.collect.server import (
    _build_handler,
    _run_clear_action,
    _run_collect_action,
    _run_export_action,
    _run_sync_action,
)


class CollectServerActionsTest(unittest.TestCase):
    def test_collect_action_forwards_expected_arguments(self) -> None:
        with patch("src.collect.server.collect_account_bundle") as collect_mock:
            collect_mock.return_value = {"output_paths": {"account": "account.json"}}
            logger = lambda message: message

            response = _run_collect_action(
                {
                    "platform": "instagram",
                    "username": "nasa",
                    "include_comments": True,
                    "max_posts": 5,
                    "max_comment_pages": 2,
                    "page_size": 12,
                    "output_root": "data/collect",
                },
                log=logger,
            )

            self.assertTrue(response["ok"])
            self.assertEqual(response["result"]["output_paths"]["account"], "account.json")
            args, kwargs = collect_mock.call_args
            self.assertEqual(args[0].platform, "instagram")
            self.assertEqual(args[0].username, "nasa")
            self.assertTrue(kwargs["include_comments"])
            self.assertEqual(kwargs["max_posts"], 5)
            self.assertEqual(kwargs["max_comment_pages"], 2)
            self.assertEqual(kwargs["page_size"], 12)
            self.assertIs(kwargs["log"], logger)

    def test_collect_action_normalizes_instagram_handle_from_user_id(self) -> None:
        with patch("src.collect.server.collect_account_bundle") as collect_mock:
            collect_mock.return_value = {"output_paths": {"account": "account.json"}}

            response = _run_collect_action(
                {
                    "platform": "instagram",
                    "user_id": "\u200b\u200b@grandma_droniak",
                }
            )

            self.assertTrue(response["ok"])
            args, _kwargs = collect_mock.call_args
            self.assertEqual(args[0].username, "grandma_droniak")
            self.assertIsNone(args[0].user_id)

    def test_export_action_uses_defaults(self) -> None:
        with patch("src.collect.server.export_dashboard_data") as export_mock:
            export_mock.return_value = {"posts": "data/dashboard/posts.json"}

            response = _run_export_action({})

            self.assertTrue(response["ok"])
            export_mock.assert_called_once_with("data/collect", output_dir="data/dashboard")

    def test_sync_action_uses_defaults(self) -> None:
        with patch("src.collect.server.sync_docs_data") as sync_mock:
            sync_mock.return_value = {"posts": "docs/data/posts.json"}

            response = _run_sync_action({})

            self.assertTrue(response["ok"])
            sync_mock.assert_called_once_with(source_dir="data/dashboard", docs_dir="docs/data")

    def test_clear_action_forwards_expected_arguments(self) -> None:
        with patch("src.collect.server.clear_results") as clear_mock:
            clear_mock.return_value = {"ok": True, "matched_runs": 1}

            response = _run_clear_action(
                {
                    "platform": "instagram",
                    "username": "nasa",
                    "user_id": "123",
                    "account_id": "456",
                    "run_id": "run-1",
                    "clear_all_on_platform": True,
                    "collect_root": "data/collect",
                    "dashboard_dir": "data/dashboard",
                    "docs_dir": "docs/data",
                }
            )

            self.assertTrue(response["ok"])
            clear_mock.assert_called_once_with(
                platform="instagram",
                username="nasa",
                user_id="123",
                account_id="456",
                run_id="run-1",
                clear_all_on_platform=True,
                collect_root="data/collect",
                dashboard_dir="data/dashboard",
                docs_dir="docs/data",
            )


class CollectServerHttpTest(unittest.TestCase):
    def test_health_endpoint_and_static_index_are_served(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            (docs_dir / "index.html").write_text("<!doctype html><p>Hello</p>", encoding="utf-8")

            handler = _build_handler(docs_dir)
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"

            try:
                with urlopen(f"{base_url}/api/health") as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])

                with urlopen(f"{base_url}/") as response:
                    html = response.read().decode("utf-8")
                self.assertIn("Hello", html)
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

    def test_collect_stream_endpoint_returns_logs_and_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            (docs_dir / "index.html").write_text("<!doctype html><p>Hello</p>", encoding="utf-8")

            handler = _build_handler(docs_dir)
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"

            def fake_collect(*args, **kwargs):
                kwargs["log"]("Fetching account profile...")
                kwargs["log"]("Collection finished.")
                return {"output_paths": {"account": "account.json"}}

            request = Request(
                f"{base_url}/api/collect-account/stream",
                data=json.dumps({"platform": "instagram", "username": "nasa"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with patch("src.collect.server.collect_account_bundle", side_effect=fake_collect):
                    with urlopen(request) as response:
                        lines = response.read().decode("utf-8").splitlines()
                events = [json.loads(line) for line in lines if line.strip()]
                self.assertEqual(events[0]["event"], "log")
                self.assertEqual(events[1]["event"], "log")
                self.assertEqual(events[2]["event"], "result")
                self.assertEqual(events[3]["event"], "complete")
                self.assertTrue(events[3]["ok"])
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
