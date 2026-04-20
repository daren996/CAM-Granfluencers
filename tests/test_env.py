from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.collect.env import load_dotenv_if_present


class DotenvLoaderTest(unittest.TestCase):
    def test_loads_dotenv_from_parent_directory_without_overriding_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            (root / ".env").write_text(
                "# comment\n"
                "TIKHUB_API_KEY=from-dotenv\n"
                "export EXTRA_VALUE='hello'\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"TIKHUB_API_KEY": "from-shell"}, clear=True):
                loaded = load_dotenv_if_present(start_dir=nested)

                self.assertEqual(loaded.resolve(), (root / ".env").resolve())
                self.assertEqual(os.environ["TIKHUB_API_KEY"], "from-shell")
                self.assertEqual(os.environ["EXTRA_VALUE"], "hello")


if __name__ == "__main__":
    unittest.main()
