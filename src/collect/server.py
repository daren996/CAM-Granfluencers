from __future__ import annotations

import json
import queue
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .client import TikHubClient
from .cleanup import clear_results
from .env import load_dotenv_if_present
from .exceptions import TikHubConfigurationError, TikHubError
from .exporter import export_dashboard_data, sync_docs_data
from .models import AccountRef
from .service import collect_account_bundle


def run_local_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    docs_dir: str | Path = "docs",
) -> int:
    load_dotenv_if_present()
    resolved_docs_dir = Path(docs_dir).resolve()
    if not resolved_docs_dir.is_dir():
        raise FileNotFoundError(f"Docs directory does not exist: {resolved_docs_dir}")

    handler = _build_handler(resolved_docs_dir)
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"Serving docs and local collect API at http://{host}:{port}")
        print(f"Docs root: {resolved_docs_dir}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
    return 0


def _build_handler(docs_dir: Path):
    class CollectRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(docs_dir), **kwargs)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "service": "collect-local-api",
                        "docs_dir": str(docs_dir),
                    },
                )
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                payload = self._read_json_body()
                if parsed.path == "/api/check":
                    self._send_json(HTTPStatus.OK, _run_check_action())
                    return
                if parsed.path == "/api/collect-account/stream":
                    self._stream_collect_action(payload)
                    return
                if parsed.path == "/api/collect-account":
                    self._send_json(HTTPStatus.OK, _run_collect_action(payload))
                    return
                if parsed.path == "/api/export-dashboard":
                    self._send_json(HTTPStatus.OK, _run_export_action(payload))
                    return
                if parsed.path == "/api/sync-docs-data":
                    self._send_json(HTTPStatus.OK, _run_sync_action(payload))
                    return
                if parsed.path == "/api/clear-results":
                    self._send_json(HTTPStatus.OK, _run_clear_action(payload))
                    return
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"ok": False, "error": f"Unknown API endpoint: {parsed.path}"},
                )
            except TikHubConfigurationError as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"ok": False, "error": str(exc), "kind": "configuration"},
                )
            except TikHubError as exc:
                status = exc.status_code or HTTPStatus.BAD_GATEWAY
                self._send_json(
                    status,
                    {
                        "ok": False,
                        "error": str(exc),
                        "kind": "tikhub",
                        "status_code": exc.status_code,
                        "url": exc.url,
                        "payload": exc.payload,
                    },
                )
            except (KeyError, ValueError, FileNotFoundError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            except Exception as exc:  # pragma: no cover - defensive server fallback
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

        def end_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            super().end_headers()

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _read_json_body(self) -> dict:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                return {}
            raw_body = self.rfile.read(content_length)
            if not raw_body:
                return {}
            return json.loads(raw_body.decode("utf-8"))

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _stream_collect_action(self, payload: dict) -> None:
            event_queue: queue.Queue[dict] = queue.Queue()

            def emit(event: str, **data) -> None:
                event_queue.put({"event": event, **data})

            def worker() -> None:
                try:
                    result = _run_collect_action(payload, log=lambda message: emit("log", message=message))
                    emit("result", data=result)
                    emit("complete", ok=True, message="Collection completed successfully.")
                except Exception as exc:  # pragma: no cover - exercised through serialized payloads
                    error_payload = _serialize_exception(exc)
                    emit("error", data=error_payload)
                    emit("complete", ok=False, message=error_payload["error"])

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()

            while True:
                event = event_queue.get()
                try:
                    self._write_stream_event(event)
                except BrokenPipeError:
                    break
                if event["event"] == "complete":
                    break

        def _write_stream_event(self, payload: dict) -> None:
            line = json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"
            self.wfile.write(line)
            self.wfile.flush()

    return CollectRequestHandler


def _run_check_action() -> dict:
    client = TikHubClient()
    user_payload, _ = client.get_user_info()
    usage_payload, _ = client.get_user_daily_usage()
    return {
        "ok": True,
        "user_info": user_payload.get("data", user_payload),
        "daily_usage": usage_payload.get("data", usage_payload),
    }


def _run_collect_action(payload: dict, log=None) -> dict:
    account_ref = AccountRef(
        platform=payload.get("platform") or "instagram",
        username=payload.get("username"),
        user_id=payload.get("user_id"),
    )
    result = collect_account_bundle(
        account_ref,
        include_comments=bool(payload.get("include_comments")),
        max_posts=payload.get("max_posts"),
        max_comment_pages=payload.get("max_comment_pages"),
        page_size=payload.get("page_size"),
        output_root=payload.get("output_root") or "data/collect",
        log=log,
    )
    return {"ok": True, "result": result}


def _run_export_action(payload: dict) -> dict:
    input_path = payload.get("input") or "data/collect"
    output_dir = payload.get("output_dir") or "data/dashboard"
    written = export_dashboard_data(input_path, output_dir=output_dir)
    return {"ok": True, "written": written}


def _run_sync_action(payload: dict) -> dict:
    source_dir = payload.get("source_dir") or "data/dashboard"
    docs_dir = payload.get("docs_dir") or "docs/data"
    written = sync_docs_data(source_dir=source_dir, docs_dir=docs_dir)
    return {"ok": True, "written": written}


def _run_clear_action(payload: dict) -> dict:
    result = clear_results(
        platform=payload.get("platform") or "instagram",
        username=payload.get("username"),
        user_id=payload.get("user_id"),
        account_id=payload.get("account_id"),
        run_id=payload.get("run_id"),
        clear_all_on_platform=bool(payload.get("clear_all_on_platform")),
        collect_root=payload.get("collect_root") or "data/collect",
        dashboard_dir=payload.get("dashboard_dir") or "data/dashboard",
        docs_dir=payload.get("docs_dir") or "docs/data",
    )
    return result


def _serialize_exception(exc: Exception) -> dict:
    if isinstance(exc, TikHubConfigurationError):
        return {"ok": False, "error": str(exc), "kind": "configuration"}
    if isinstance(exc, TikHubError):
        return {
            "ok": False,
            "error": str(exc),
            "kind": "tikhub",
            "status_code": exc.status_code,
            "url": exc.url,
            "payload": exc.payload,
        }
    if isinstance(exc, (KeyError, ValueError, FileNotFoundError)):
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": str(exc)}
