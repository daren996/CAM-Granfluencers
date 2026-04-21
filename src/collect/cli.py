from __future__ import annotations

import argparse
import json
import sys

from .client import TikHubClient
from .cleanup import clear_results
from .env import load_dotenv_if_present
from .exceptions import TikHubConfigurationError, TikHubError
from .models import AccountRef
from .service import collect_account_bundle
from .exporter import export_dashboard_data, sync_docs_data
from .server import run_local_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect and export social platform data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser(
        "collect-account", help="Collect one account bundle from a supported platform."
    )
    collect_parser.add_argument("--platform", required=True, help="Platform name, e.g. instagram.")
    collect_parser.add_argument("--username", help="Platform username.")
    collect_parser.add_argument("--user-id", help="Platform numeric user id.")
    collect_parser.add_argument(
        "--include-comments",
        action="store_true",
        help="Collect comments and second-level replies for each post.",
    )
    collect_parser.add_argument("--max-posts", type=int, help="Maximum number of posts to collect.")
    collect_parser.add_argument(
        "--max-comment-pages",
        type=int,
        help="Maximum pages per comments or replies pagination loop.",
    )
    collect_parser.add_argument("--page-size", type=int, help="Page size for post pagination.")
    collect_parser.add_argument(
        "--output-root",
        default="data/collect",
        help="Directory for raw and normalized collection output.",
    )

    export_parser = subparsers.add_parser(
        "export-dashboard", help="Export dashboard JSON files from collected account and item data."
    )
    export_parser.add_argument(
        "--input",
        required=True,
        help="Path to data/collect, account.json, item.json, or a legacy bundle.json file.",
    )
    export_parser.add_argument(
        "--output-dir",
        default="data/dashboard",
        help="Dashboard data output directory.",
    )

    sync_parser = subparsers.add_parser(
        "sync-docs-data",
        help="Copy dashboard JSON files into docs/data for the published site.",
    )
    sync_parser.add_argument(
        "--source-dir",
        default="data/dashboard",
        help="Canonical dashboard data directory.",
    )
    sync_parser.add_argument(
        "--docs-dir",
        default="docs/data",
        help="Published docs data directory.",
    )

    clear_parser = subparsers.add_parser(
        "clear-results",
        help="Remove matching collected account trees or legacy runs, then rebuild exports.",
    )
    clear_parser.add_argument("--platform", required=True, help="Platform name, e.g. instagram.")
    clear_parser.add_argument("--username", help="Platform username.")
    clear_parser.add_argument("--user-id", help="Platform numeric user id.")
    clear_parser.add_argument("--account-id", help="Collected account id stored in profile data.")
    clear_parser.add_argument("--run-id", help="Specific legacy run id to clear.")
    clear_parser.add_argument(
        "--clear-all-on-platform",
        action="store_true",
        help="Allow clearing all results for the selected platform when no identifier is provided.",
    )
    clear_parser.add_argument(
        "--collect-root",
        default="data/collect",
        help="Directory containing collected account trees and legacy bundle runs.",
    )
    clear_parser.add_argument(
        "--dashboard-dir",
        default="data/dashboard",
        help="Canonical dashboard data directory.",
    )
    clear_parser.add_argument(
        "--docs-dir",
        default="docs/data",
        help="Published docs data directory.",
    )

    serve_parser = subparsers.add_parser(
        "serve",
        help="Serve docs/ locally together with a local API for interactive collection actions.",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind the local server.")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port for the local server.")
    serve_parser.add_argument(
        "--docs-dir",
        default="docs",
        help="Directory of static docs files to serve.",
    )

    subparsers.add_parser(
        "check",
        help="Hit the TikHub user endpoints to verify the API key and print balance / daily usage.",
    )
    return parser


def main() -> int:
    load_dotenv_if_present()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "collect-account":
        account_ref = AccountRef(
            platform=args.platform,
            username=args.username,
            user_id=args.user_id,
        )
        result = collect_account_bundle(
            account_ref,
            include_comments=args.include_comments,
            max_posts=args.max_posts,
            max_comment_pages=args.max_comment_pages,
            page_size=args.page_size,
            output_root=args.output_root,
        )
        print(json.dumps(result["output_paths"], indent=2, ensure_ascii=True))
        return 0

    if args.command == "export-dashboard":
        written = export_dashboard_data(args.input, output_dir=args.output_dir)
        print(json.dumps(written, indent=2, ensure_ascii=True))
        return 0

    if args.command == "sync-docs-data":
        written = sync_docs_data(args.source_dir, docs_dir=args.docs_dir)
        print(json.dumps(written, indent=2, ensure_ascii=True))
        return 0

    if args.command == "clear-results":
        result = clear_results(
            platform=args.platform,
            username=args.username,
            user_id=args.user_id,
            account_id=args.account_id,
            run_id=args.run_id,
            clear_all_on_platform=args.clear_all_on_platform,
            collect_root=args.collect_root,
            dashboard_dir=args.dashboard_dir,
            docs_dir=args.docs_dir,
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0

    if args.command == "serve":
        return run_local_server(host=args.host, port=args.port, docs_dir=args.docs_dir)

    if args.command == "check":
        return _run_check()

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_check() -> int:
    """Online smoke check: verify the API key works and print balance / daily usage.

    Exit codes:
      0 - success
      2 - missing or invalid local configuration (e.g. TIKHUB_API_KEY not set)
      1 - the API rejected the request (auth, payment, rate limit, transient, ...)
    """
    try:
        client = TikHubClient()
    except TikHubConfigurationError as exc:
        print(f"check: configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        user_payload, _ = client.get_user_info()
        usage_payload, _ = client.get_user_daily_usage()
    except TikHubError as exc:
        status = f" [HTTP {exc.status_code}]" if exc.status_code else ""
        print(f"check: TikHub request failed{status}: {exc}", file=sys.stderr)
        return 1

    summary = {
        "user_info": user_payload.get("data", user_payload),
        "daily_usage": usage_payload.get("data", usage_payload),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0
