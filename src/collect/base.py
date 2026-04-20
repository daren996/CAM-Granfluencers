from __future__ import annotations

from abc import ABC, abstractmethod

from .models import AccountRef, Cursor, PageEnvelope, PostRef, RecordEnvelope


class BaseCollector(ABC):
    """Common interface shared across platform collectors."""

    platform: str

    @abstractmethod
    def fetch_account_profile(self, account_ref: AccountRef) -> RecordEnvelope:
        raise NotImplementedError

    @abstractmethod
    def fetch_account_posts(
        self, account_ref: AccountRef, cursor: Cursor = None, page_size: int | None = None
    ) -> PageEnvelope:
        raise NotImplementedError

    @abstractmethod
    def fetch_post_detail(self, post_ref: PostRef) -> RecordEnvelope:
        raise NotImplementedError

    @abstractmethod
    def fetch_post_comments(
        self, post_ref: PostRef, cursor: Cursor = None, sort: str = "popular"
    ) -> PageEnvelope:
        raise NotImplementedError

    @abstractmethod
    def fetch_comment_replies(
        self, post_ref: PostRef, comment_id: str, cursor: Cursor = None
    ) -> PageEnvelope:
        raise NotImplementedError

    @abstractmethod
    def search_accounts(self, query: str) -> PageEnvelope:
        raise NotImplementedError
