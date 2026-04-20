from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_if_present(filename: str = ".env", start_dir: str | Path | None = None) -> Path | None:
    """Load a simple .env file into os.environ without overriding existing values."""

    start_path = Path(start_dir or Path.cwd()).resolve()
    for directory in (start_path, *start_path.parents):
        candidate = directory / filename
        if candidate.is_file():
            _load_dotenv_file(candidate)
            return candidate
    return None


def _load_dotenv_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value
