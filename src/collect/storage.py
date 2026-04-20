from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return path


def make_run_dir(output_root: str | Path, platform: str, account_slug: str, run_id: str) -> Path:
    return Path(output_root) / platform / account_slug / run_id


def write_raw_snapshot(
    run_dir: Path,
    *,
    category: str,
    name: str,
    payload: dict[str, Any],
) -> Path:
    safe_name = name.replace("/", "_")
    return write_json(run_dir / "raw" / category / f"{safe_name}.json", payload)
