"""The project's own search index (long-tail sample): store, ingestion, crawler.

CLI: python3 -m server.index --help
"""
import os
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "index" / "local.sqlite"


def index_path() -> Path:
    return Path(os.environ.get("LOCAL_INDEX_PATH") or DEFAULT_PATH)
