"""SQLite database initialization utilities for Better GI MiniWeb."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app import PostData, app, db, save_webhook_payload

# Historical class name kept for compatibility with older local scripts.
Post_data = PostData
POST_LOAD_DIR = Path("post_load")


def init_db() -> None:
    """Create all SQLite tables if they do not already exist."""

    with app.app_context():
        print("Initializing database...")
        db.create_all()
        print("Database initialized.")


def write_json_to_db(post_load_dir: Path = POST_LOAD_DIR) -> None:
    """Import captured webhook JSON files from ``post_load`` if present."""

    if not post_load_dir.exists():
        return

    with app.app_context():
        for file_path in sorted(post_load_dir.glob("*.txt")):
            with file_path.open("r", encoding="utf-8") as file:
                captured_request: dict[str, Any] = json.load(file)
            payload = captured_request.get("json")
            if isinstance(payload, dict):
                save_webhook_payload(payload)


if __name__ == "__main__":
    init_db()
    write_json_to_db()
