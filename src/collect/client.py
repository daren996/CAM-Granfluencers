from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib import error, parse, request

from .exceptions import (
    TikHubAuthenticationError,
    TikHubConfigurationError,
    TikHubError,
    TikHubPaymentRequiredError,
    TikHubRateLimitError,
    TikHubTransientError,
)


Transport = Callable[[str, str, dict[str, str], float], "TransportResult"]


@dataclass
class TransportResult:
    status_code: int
    payload: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)


class TikHubClient:
    """Low-level HTTP client for TikHub endpoints."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.tikhub.io",
        user_agent: str = "CAM-Granfluencers/0.1",
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
        transport: Transport | None = None,
    ) -> None:
        resolved_key = api_key or os.getenv("TIKHUB_API_KEY")
        if not resolved_key:
            raise TikHubConfigurationError(
                "TIKHUB_API_KEY is required to call TikHub endpoints."
            )
        self.api_key = resolved_key
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.sleep = sleep
        self.transport = transport or self._default_transport

    @property
    def auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        query = {
            key: value
            for key, value in (params or {}).items()
            if value is not None and value != ""
        }
        query_string = parse.urlencode(query, doseq=True)
        url = f"{self.base_url}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        attempt = 0
        while True:
            attempt += 1
            result = self.transport("GET", url, self.auth_header, self.timeout)
            if 200 <= result.status_code < 300:
                embedded_error = self._embedded_error_result(result.payload)
                if embedded_error is None:
                    meta = self._build_request_meta(path, url, query, result.payload)
                    return result.payload, meta

                exc = self._error_from_result(embedded_error, url)
                if not self._should_retry(embedded_error.status_code, attempt):
                    raise exc

                self.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                continue

            exc = self._error_from_result(result, url)
            if not self._should_retry(result.status_code, attempt):
                raise exc

            self.sleep(self.backoff_factor * (2 ** (attempt - 1)))

    def get_user_info(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.get("/api/v1/tikhub/user/get_user_info")

    def get_user_daily_usage(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.get("/api/v1/tikhub/user/get_user_daily_usage")

    def _should_retry(self, status_code: int, attempt: int) -> bool:
        retryable = status_code == 429 or status_code >= 500
        return retryable and attempt <= self.max_retries

    def _error_from_result(self, result: TransportResult, url: str) -> TikHubError:
        message = (
            result.payload.get("message")
            or result.payload.get("detail")
            or f"TikHub request failed with status {result.status_code}."
        )
        if result.status_code == 401:
            return TikHubAuthenticationError(
                message, status_code=401, payload=result.payload, url=url
            )
        if result.status_code == 402:
            return TikHubPaymentRequiredError(
                message, status_code=402, payload=result.payload, url=url
            )
        if result.status_code == 429:
            return TikHubRateLimitError(
                message, status_code=429, payload=result.payload, url=url
            )
        if result.status_code >= 500:
            return TikHubTransientError(
                message, status_code=result.status_code, payload=result.payload, url=url
            )
        return TikHubError(
            message,
            status_code=result.status_code,
            payload=result.payload,
            url=url,
        )

    def _build_request_meta(
        self,
        path: str,
        url: str,
        params: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "source_endpoint": path,
            "request_url": url,
            "request_params": params,
            "fetched_at": payload.get("time"),
            "request_id": payload.get("request_id"),
            "router": payload.get("router"),
            "docs": payload.get("docs"),
            "cache_url": payload.get("cache_url"),
            "cache_message": payload.get("cache_message"),
            "cache_message_zh": payload.get("cache_message_zh"),
        }

    def _embedded_error_result(self, payload: dict[str, Any]) -> TransportResult | None:
        data = payload.get("data")
        if not isinstance(data, dict):
            return None

        nested_code = data.get("code")
        if isinstance(nested_code, str) and nested_code.isdigit():
            nested_code = int(nested_code)
        if not isinstance(nested_code, int):
            return None
        if 200 <= nested_code < 300:
            return None

        return TransportResult(
            status_code=nested_code,
            payload={
                **data,
                "upstream_request_id": payload.get("request_id"),
                "upstream_router": payload.get("router"),
                "upstream_docs": payload.get("docs"),
            },
        )

    def _default_transport(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        timeout: float,
    ) -> TransportResult:
        req = request.Request(url=url, method=method, headers=headers)
        try:
            with request.urlopen(req, timeout=timeout) as response:
                payload = self._read_json(response.read())
                response_headers = dict(response.headers.items())
                return TransportResult(
                    status_code=response.getcode(),
                    payload=payload,
                    headers=response_headers,
                )
        except error.HTTPError as exc:
            payload = self._read_json(exc.read())
            return TransportResult(
                status_code=exc.code,
                payload=payload,
                headers=dict(exc.headers.items()),
            )
        except error.URLError as exc:
            raise TikHubTransientError(str(exc.reason), url=url) from exc

    def _read_json(self, payload: bytes) -> dict[str, Any]:
        if not payload:
            return {}
        try:
            return json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            return {"raw_text": payload.decode("utf-8", errors="replace")}
