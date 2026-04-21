from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request


@dataclass
class DownloadedAsset:
    source_url: str
    content_type: str | None
    size_bytes: int
    path: Path


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return path


def make_account_dir(output_root: str | Path, platform: str, account_slug: str) -> Path:
    return Path(output_root) / platform / account_slug


def make_item_dir(
    output_root: str | Path,
    platform: str,
    account_slug: str,
    item_group: str,
    item_slug: str,
) -> Path:
    return make_account_dir(output_root, platform, account_slug) / item_group / item_slug


def write_raw_snapshot(
    root_dir: Path,
    *,
    category: str,
    name: str,
    payload: dict[str, Any],
) -> Path:
    safe_name = name.replace("/", "_")
    return write_json(root_dir / "raw" / category / f"{safe_name}.json", payload)


def write_raw_json(root_dir: Path, relative_path: str | Path, payload: dict[str, Any]) -> Path:
    return write_json(root_dir / "raw" / Path(relative_path), payload)


def download_remote_asset(
    url: str,
    output_dir: Path,
    *,
    stem: str,
    timeout: float = 30.0,
) -> DownloadedAsset:
    req = request.Request(url=url, headers={"User-Agent": "CAM-Granfluencers/0.1"})
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read()
            headers = dict(response.headers.items())
            resolved_url = response.geturl() or url
    except error.URLError as exc:
        raise RuntimeError(f"Failed to download asset: {url}") from exc

    content_type = headers.get("Content-Type")
    suffix = _asset_suffix(resolved_url, content_type)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = stem.replace("/", "_")
    path = output_dir / f"{safe_stem}{suffix}"
    path.write_bytes(payload)
    return DownloadedAsset(
        source_url=url,
        content_type=content_type,
        size_bytes=len(payload),
        path=path,
    )


def _asset_suffix(url: str, content_type: str | None) -> str:
    parsed = parse.urlparse(url)
    suffix = Path(parse.unquote(parsed.path)).suffix.lower()
    if suffix:
        return suffix

    if not content_type:
        return ".bin"

    guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
    if guessed == ".jpe":
        return ".jpg"
    return guessed or ".bin"
