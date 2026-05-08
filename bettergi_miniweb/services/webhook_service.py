"""Service helpers for validating and persisting BetterGI webhook payloads."""

from __future__ import annotations

from typing import Any

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


def save_webhook_payload(payload: dict[str, Any]) -> PostData:
    """Normalize and commit one BetterGI webhook event through SQLAlchemy."""

    normalized = normalize_webhook_payload(payload)
    record = PostData(**normalized)
    db.session.add(record)
    db.session.commit()
    return record
