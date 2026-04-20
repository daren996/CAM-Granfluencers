#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SUITES = {
    "client": ["tests.test_client"],
    "collect": [
        "tests.test_client",
        "tests.test_env",
        "tests.test_instagram_collector",
        "tests.test_exporter",
        "tests.test_service_integration",
    ],
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run project test suites.")
    parser.add_argument(
        "suite",
        nargs="?",
        default="all",
        choices=["all", *sorted(SUITES)],
        help="Named test suite to run.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    if args.suite == "all":
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    else:
        modules = SUITES[args.suite]
        cmd = [sys.executable, "-m", "unittest", *modules]

    print(f"Running test suite: {args.suite}")
    print(" ".join(cmd))
    completed = subprocess.run(cmd, cwd=repo_root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
