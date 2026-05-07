"""Backward-compatible imports for older entry points.

New code should import from :mod:`app` directly. This module keeps historical
``from main import app`` usage working for existing launch scripts.
"""

from app import PostData, app, create_app, db, save_webhook_payload

# Historical class name kept as an alias so older external scripts do not break.
Post_data = PostData
save_data = save_webhook_payload

__all__ = [
    "PostData",
    "Post_data",
    "app",
    "create_app",
    "db",
    "save_data",
    "save_webhook_payload",
]
