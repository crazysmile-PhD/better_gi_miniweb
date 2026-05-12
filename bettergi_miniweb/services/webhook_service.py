"""Service helpers for validating and persisting BetterGI webhook payloads."""

from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any

from flask import current_app

from bettergi_miniweb.extensions import db
from bettergi_miniweb.models import PostData

WEBHOOK_FIELDS = ("result", "timestamp", "message", "screenshot")


def normalize_webhook_payload(payload: dict[str, Any]) -> dict[str, str | None]:
    """Return DB-ready webhook fields or raise ValueError for invalid payloads."""

    event = payload.get("event")
    if not isinstance(event, str) or not event.strip():
        raise ValueError("Webhook payload must include a non-empty string field: event")

    normalized: dict[str, str | None] = {"event": event.strip()}
    for field in WEBHOOK_FIELDS:
        value = payload.get(field)
        normalized[field] = None if value is None else str(value)
    return normalized


def _screenshot_storage_root() -> Path:
    storage_dir = current_app.config["SCREENSHOT_STORAGE_DIR"]
    root = Path(storage_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _relative_screenshot_name(record_id: int) -> str:
    return f"post_{record_id}.png"


def resolve_screenshot_path(relative_path: str | None) -> Path | None:
    """Resolve a DB screenshot path only if it remains inside the storage root."""

    if not relative_path:
        return None

    root = _screenshot_storage_root()
    candidate = (root / relative_path).resolve()
    if candidate == root or root not in candidate.parents:
        current_app.logger.warning("Rejected unsafe screenshot path: %s", relative_path)
        return None
    return candidate


def _persist_screenshot_file(record: PostData, screenshot: str) -> Path | None:
    """Decode and write a screenshot file, returning None for legacy-invalid data."""

    try:
        binary_data = base64.b64decode(screenshot, validate=True)
    except (binascii.Error, ValueError):
        return None

    relative_name = _relative_screenshot_name(record.id)
    target = resolve_screenshot_path(relative_name)
    if target is None:
        raise ValueError("Unable to resolve screenshot storage path")

    target.write_bytes(binary_data)
    record.screenshot = None
    record.screenshot_path = relative_name
    return target


def _cleanup_screenshot_file(path: Path | None) -> None:
    if path is None:
        return

    try:
        path.unlink(missing_ok=True)
    except OSError:
        current_app.logger.exception("Failed to clean up orphan screenshot file: %s", path)


def save_webhook_payload(payload: dict[str, Any]) -> PostData:
    """Normalize and commit one BetterGI webhook event through SQLAlchemy."""

    normalized = normalize_webhook_payload(payload)
    screenshot = normalized.pop("screenshot", None)
    record = PostData(**normalized, screenshot=None)
    written_screenshot: Path | None = None

    try:
        db.session.add(record)
        db.session.flush()

        if screenshot:
            written_screenshot = _persist_screenshot_file(record, screenshot)
            if written_screenshot is None:
                record.screenshot = screenshot

        db.session.commit()
    except Exception:
        db.session.rollback()
        _cleanup_screenshot_file(written_screenshot)
        raise

    return record
