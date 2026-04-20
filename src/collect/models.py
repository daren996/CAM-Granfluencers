from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Cursor = str | None


@dataclass(frozen=True)
class AccountRef:
    """Stable account identifier shared across platform collectors."""

    platform: str
    username: str | None = None
    user_id: str | None = None

    def __post_init__(self) -> None:
        if not self.username and not self.user_id:
            raise ValueError("AccountRef requires either username or user_id.")

    def to_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.username:
            params["username"] = self.username
        if self.user_id:
            params["user_id"] = self.user_id
        return params

    @property
    def slug(self) -> str:
        return self.username or str(self.user_id)


@dataclass(frozen=True)
class PostRef:
    """Stable post identifier shared across platform collectors."""

    platform: str
    media_id: str | None = None
    shortcode: str | None = None
    url: str | None = None

    def __post_init__(self) -> None:
        if not any((self.media_id, self.shortcode, self.url)):
            raise ValueError("PostRef requires media_id, shortcode, or url.")

    def to_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.media_id:
            params["media_id"] = self.media_id
        if self.shortcode:
            params["code"] = self.shortcode
        if self.url:
            params["url"] = self.url
        return params

    @property
    def slug(self) -> str:
        return self.shortcode or self.media_id or "post"


@dataclass
class RecordEnvelope:
    """Normalized single-record result plus raw response and request metadata."""

    record: dict[str, Any]
    raw_payload: dict[str, Any]
    request_meta: dict[str, Any]


@dataclass
class PageEnvelope:
    """Normalized paginated result plus raw response and cursor information."""

    records: list[dict[str, Any]]
    raw_payload: dict[str, Any]
    request_meta: dict[str, Any]
    next_cursor: Cursor = None
    has_next_page: bool = False


@dataclass
class CollectionBundle:
    """Persisted output for one collection run."""

    run_id: str
    platform: str
    account_ref: dict[str, Any]
    collected_at: str
    include_comments: bool
    profile: dict[str, Any]
    posts: list[dict[str, Any]] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    replies: list[dict[str, Any]] = field(default_factory=list)
    request_log: list[dict[str, Any]] = field(default_factory=list)
    output_paths: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "platform": self.platform,
            "account_ref": self.account_ref,
            "collected_at": self.collected_at,
            "include_comments": self.include_comments,
            "profile": self.profile,
            "posts": self.posts,
            "comments": self.comments,
            "replies": self.replies,
            "request_log": self.request_log,
            "output_paths": self.output_paths,
        }
