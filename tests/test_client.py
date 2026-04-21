from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.collect.client import TikHubClient, TransportResult
from src.collect.exceptions import (
    TikHubAuthenticationError,
    TikHubConfigurationError,
    TikHubError,
    TikHubPaymentRequiredError,
    TikHubRateLimitError,
)


class TikHubClientTest(unittest.TestCase):
    def test_auth_header_uses_bearer_token(self) -> None:
        client = TikHubClient(api_key="demo-token", transport=_static_transport({}))
        self.assertEqual(client.auth_header["Authorization"], "Bearer demo-token")
        self.assertEqual(client.auth_header["User-Agent"], "CAM-Granfluencers/0.1")
        self.assertEqual(client.auth_header["Accept"], "application/json")

    def test_missing_api_key_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(TikHubConfigurationError):
                TikHubClient(transport=_static_transport({}))

    def test_maps_401_to_authentication_error(self) -> None:
        client = TikHubClient(
            api_key="demo-token",
            max_retries=0,
            transport=lambda method, url, headers, timeout: TransportResult(
                status_code=401,
                payload={"message": "Invalid API token."},
            ),
        )
        with self.assertRaises(TikHubAuthenticationError):
            client.get("/api/v1/example")

    def test_maps_402_to_payment_required_error(self) -> None:
        client = TikHubClient(
            api_key="demo-token",
            max_retries=0,
            transport=lambda method, url, headers, timeout: TransportResult(
                status_code=402,
                payload={"message": "Insufficient balance."},
            ),
        )
        with self.assertRaises(TikHubPaymentRequiredError):
            client.get("/api/v1/example")

    def test_maps_429_to_rate_limit_error(self) -> None:
        client = TikHubClient(
            api_key="demo-token",
            max_retries=0,
            transport=lambda method, url, headers, timeout: TransportResult(
                status_code=429,
                payload={"message": "Too many requests."},
            ),
        )
        with self.assertRaises(TikHubRateLimitError):
            client.get("/api/v1/example")

    def test_raises_when_tikhub_embeds_error_in_200_response(self) -> None:
        client = TikHubClient(
            api_key="demo-token",
            max_retries=0,
            transport=lambda method, url, headers, timeout: TransportResult(
                status_code=200,
                payload={
                    "request_id": "req-1",
                    "router": "/api/v1/example",
                    "docs": "https://api.tikhub.io/docs/example",
                    "data": {
                        "code": 400,
                        "message": "User lookup returned null",
                        "data": None,
                    },
                },
            ),
        )

        with self.assertRaises(TikHubError) as ctx:
            client.get("/api/v1/example")

        self.assertEqual(str(ctx.exception), "User lookup returned null")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.payload["upstream_request_id"], "req-1")


def _static_transport(payload):
    def transport(method, url, headers, timeout):
        return TransportResult(status_code=200, payload=payload)

    return transport


if __name__ == "__main__":
    unittest.main()
