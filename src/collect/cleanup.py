from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exporter import export_dashboard_data, sync_docs_data


@dataclass(frozen=True)
class ClearFilters:
    platform: str
    username: str | None = None
    user_id: str | None = None
    account_id: str | None = None
    run_id: str | None = None
    clear_all_on_platform: bool = False

    @property
    def has_identifier(self) -> bool:
        return any((self.username, self.user_id, self.account_id, self.run_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "username": self.username,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "run_id": self.run_id,
            "clear_all_on_platform": self.clear_all_on_platform,
        }


def clear_results(
    *,
    platform: str,
    username: str | None = None,
    user_id: str | None = None,
    account_id: str | None = None,
    run_id: str | None = None,
    clear_all_on_platform: bool = False,
    collect_root: str | Path = "data/collect",
    dashboard_dir: str | Path = "data/dashboard",
    docs_dir: str | Path = "docs/data",
) -> dict[str, Any]:
    filters = ClearFilters(
        platform=_normalize_platform(platform),
        username=_normalize_value(username),
        user_id=_normalize_value(user_id),
        account_id=_normalize_value(account_id),
        run_id=_normalize_value(run_id),
        clear_all_on_platform=bool(clear_all_on_platform),
    )
    _validate_filters(filters)

    collect_root_path = Path(collect_root)
    dashboard_path = Path(dashboard_dir)
    docs_path = Path(docs_dir)

    matched_entries_before = _find_matching_entries(collect_root_path, filters)
    targets = _build_targets(filters, matched_entries_before)
    checks_before = {
        "data_collect": _summarize_collect_matches(matched_entries_before),
        "data_dashboard": _inspect_export_directory(dashboard_path, targets),
        "docs_data": _inspect_export_directory(docs_path, targets),
    }

    deleted_paths: list[str] = []
    for match in matched_entries_before:
        target_dir = Path(match["target_dir"])
        if target_dir.exists():
            shutil.rmtree(target_dir)
            deleted_paths.append(str(target_dir))
            _cleanup_empty_dirs(target_dir.parent, stop_at=collect_root_path)

    written_dashboard = export_dashboard_data(collect_root_path, output_dir=dashboard_path)
    written_docs = sync_docs_data(source_dir=dashboard_path, docs_dir=docs_path)

    matched_entries_after = _find_matching_entries(collect_root_path, filters)
    checks_after = {
        "data_collect": _summarize_collect_matches(matched_entries_after),
        "data_dashboard": _inspect_export_directory(dashboard_path, targets),
        "docs_data": _inspect_export_directory(docs_path, targets),
    }

    return {
        "ok": True,
        "filters": filters.to_dict(),
        "matched_entries": len(matched_entries_before),
        "matched_runs": len(matched_entries_before),
        "deleted_paths": deleted_paths,
        "deleted_run_dirs": deleted_paths,
        "written": {
            "dashboard": written_dashboard,
            "docs_data": written_docs,
        },
        "checks": {
            "before": checks_before,
            "after": checks_after,
        },
    }


def _validate_filters(filters: ClearFilters) -> None:
    if not filters.platform:
        raise ValueError("Clear results requires a platform.")
    if not filters.clear_all_on_platform and not filters.has_identifier:
        raise ValueError(
            "Provide username, user_id, account_id, or run_id. "
            "To clear all results on one platform, enable clear_all_on_platform."
        )


def _find_matching_entries(collect_root: Path, filters: ClearFilters) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen_target_dirs: set[str] = set()

    for account_path in sorted(collect_root.rglob("account.json")):
        account_doc = _load_json(account_path)
        if not _account_doc_matches(account_doc, filters):
            continue
        target_dir = str(account_path.parent)
        if target_dir in seen_target_dirs:
            continue
        seen_target_dirs.add(target_dir)
        matches.append(_summarize_account_doc(account_path, account_doc))

    for bundle_path in sorted(collect_root.rglob("bundle.json")):
        bundle = _load_json(bundle_path)
        if not _bundle_matches(bundle, bundle_path, filters):
            continue
        target_dir = str(bundle_path.parent)
        if target_dir in seen_target_dirs:
            continue
        seen_target_dirs.add(target_dir)
        matches.append(_summarize_bundle(bundle_path, bundle))

    return matches


def _account_doc_matches(account_doc: dict[str, Any], filters: ClearFilters) -> bool:
    if filters.run_id:
        return False

    profile = account_doc.get("profile") or {}
    account_ref = account_doc.get("account_ref") or {}
    platform = _normalize_platform(account_doc.get("platform") or profile.get("platform"))
    if platform != filters.platform:
        return False

    username_candidates = {
        _normalize_value(account_ref.get("username")),
        _normalize_value(profile.get("username")),
    }
    account_id_candidates = {
        _normalize_value(account_ref.get("user_id")),
        _normalize_value(profile.get("account_id")),
    }

    if filters.username and filters.username not in username_candidates:
        return False
    if filters.user_id and filters.user_id not in account_id_candidates:
        return False
    if filters.account_id and filters.account_id not in account_id_candidates:
        return False
    return True


def _bundle_matches(bundle: dict[str, Any], bundle_path: Path, filters: ClearFilters) -> bool:
    platform = _normalize_platform(bundle.get("platform"))
    if platform != filters.platform:
        return False

    profile = bundle.get("profile") or {}
    account_ref = bundle.get("account_ref") or {}

    username_candidates = {
        _normalize_value(account_ref.get("username")),
        _normalize_value(profile.get("username")),
    }
    account_id_candidates = {
        _normalize_value(account_ref.get("user_id")),
        _normalize_value(profile.get("account_id")),
    }
    run_id_candidates = {
        _normalize_value(bundle.get("run_id")),
        _normalize_value(bundle_path.parent.name),
    }

    if filters.username and filters.username not in username_candidates:
        return False
    if filters.user_id and filters.user_id not in account_id_candidates:
        return False
    if filters.account_id and filters.account_id not in account_id_candidates:
        return False
    if filters.run_id and filters.run_id not in run_id_candidates:
        return False
    return True


def _summarize_account_doc(account_path: Path, account_doc: dict[str, Any]) -> dict[str, Any]:
    profile = account_doc.get("profile") or {}
    account_ref = account_doc.get("account_ref") or {}
    return {
        "storage_kind": "account_tree",
        "platform": account_doc.get("platform") or profile.get("platform"),
        "run_id": None,
        "username": profile.get("username") or account_ref.get("username"),
        "account_id": profile.get("account_id") or account_ref.get("user_id"),
        "collected_at": account_doc.get("extracted_at") or account_doc.get("collected_at"),
        "bundle_path": None,
        "account_path": str(account_path),
        "target_dir": str(account_path.parent),
    }


def _summarize_bundle(bundle_path: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    profile = bundle.get("profile") or {}
    account_ref = bundle.get("account_ref") or {}
    return {
        "storage_kind": "legacy_bundle",
        "platform": bundle.get("platform"),
        "run_id": bundle.get("run_id") or bundle_path.parent.name,
        "username": profile.get("username") or account_ref.get("username"),
        "account_id": profile.get("account_id") or account_ref.get("user_id"),
        "collected_at": bundle.get("collected_at"),
        "bundle_path": str(bundle_path),
        "account_path": None,
        "target_dir": str(bundle_path.parent),
    }


def _build_targets(
    filters: ClearFilters,
    matched_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_targets: list[dict[str, Any]] = []

    for match in matched_entries:
        raw_targets.append(
            {
                "platform": _normalize_platform(match.get("platform")),
                "username": _normalize_value(match.get("username")),
                "account_id": _normalize_value(match.get("account_id")),
            }
        )

    if not raw_targets:
        raw_targets.append(
            {
                "platform": filters.platform,
                "username": filters.username,
                "account_id": filters.account_id or filters.user_id,
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for target in raw_targets:
        key = (target.get("platform"), target.get("username"), target.get("account_id"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(target)
    return deduped


def _inspect_export_directory(path: Path, targets: list[dict[str, Any]]) -> dict[str, Any]:
    accounts_path = path / "accounts.json"
    posts_path = path / "posts.json"
    accounts = _load_json_list(accounts_path)
    posts = _load_json_list(posts_path)

    matching_accounts = [item for item in accounts if _entry_matches_any_target(item, targets)]
    matching_posts = [item for item in posts if _entry_matches_any_target(item, targets)]

    return {
        "directory": str(path),
        "files_present": {
            "accounts.json": accounts_path.exists(),
            "posts.json": posts_path.exists(),
        },
        "matching_accounts": len(matching_accounts),
        "matching_posts": len(matching_posts),
        "has_matching_results": bool(matching_accounts or matching_posts),
    }


def _entry_matches_any_target(entry: dict[str, Any], targets: list[dict[str, Any]]) -> bool:
    for target in targets:
        if _entry_matches_target(entry, target):
            return True
    return False


def _entry_matches_target(entry: dict[str, Any], target: dict[str, Any]) -> bool:
    if target.get("platform") and _normalize_platform(entry.get("platform")) != target["platform"]:
        return False

    username = _normalize_value(entry.get("username"))
    account_id = _normalize_value(entry.get("account_id"))

    if target.get("username") and username != target["username"]:
        return False
    if target.get("account_id") and account_id != target["account_id"]:
        return False
    return True


def _summarize_collect_matches(matches: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "matching_entries": len(matches),
        "matching_runs": len(matches),
        "runs": matches,
        "has_matching_results": bool(matches),
    }


def _cleanup_empty_dirs(path: Path, *, stop_at: Path) -> None:
    current = path
    stop_path = stop_at.resolve()
    while current.exists() and current.resolve() != stop_path:
        if any(current.iterdir()):
            break
        current.rmdir()
        current = current.parent


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _normalize_platform(value: Any) -> str | None:
    normalized = _normalize_value(value)
    return normalized.lower() if normalized else None


def _normalize_value(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
