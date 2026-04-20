"""Collection interfaces and entrypoints for social platform data."""

from .models import AccountRef, Cursor, PageEnvelope, PostRef, RecordEnvelope
from .service import collect_account_bundle, export_dashboard_data, get_collector

__all__ = [
    "AccountRef",
    "Cursor",
    "PageEnvelope",
    "PostRef",
    "RecordEnvelope",
    "collect_account_bundle",
    "export_dashboard_data",
    "get_collector",
]
