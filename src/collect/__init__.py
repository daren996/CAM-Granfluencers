"""Collection interfaces and entrypoints for social platform data."""

from .cleanup import clear_results
from .exporter import export_dashboard_data
from .models import AccountRef, Cursor, PageEnvelope, PostRef, RecordEnvelope
from .service import collect_account_bundle, get_collector

__all__ = [
    "AccountRef",
    "Cursor",
    "PageEnvelope",
    "PostRef",
    "RecordEnvelope",
    "clear_results",
    "collect_account_bundle",
    "export_dashboard_data",
    "get_collector",
]
