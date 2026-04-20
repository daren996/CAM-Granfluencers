from __future__ import annotations

from typing import Any


class TikHubError(RuntimeError):
    """Base error for TikHub transport and collector failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: dict[str, Any] | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}
        self.url = url


class TikHubConfigurationError(TikHubError):
    """Missing local configuration such as API keys."""


class TikHubAuthenticationError(TikHubError):
    """Raised when the API key is invalid or expired."""


class TikHubPaymentRequiredError(TikHubError):
    """Raised when account balance is insufficient for an endpoint."""


class TikHubRateLimitError(TikHubError):
    """Raised after retrying rate-limited requests."""


class TikHubTransientError(TikHubError):
    """Raised when transient server errors persist after retries."""
