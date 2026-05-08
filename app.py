"""Backward-compatible Flask entry point for Better GI MiniWeb.

The application factory lives in :mod:`bettergi_miniweb.app_factory`, but this
module continues to expose the historical ``app`` object and helper imports for
gunicorn, gevent, ``flask run``, and older local scripts.
"""

from __future__ import annotations

from bettergi_miniweb import (
    PostData,
    create_app,
    db,
    normalize_webhook_payload,
    save_webhook_payload,
)
from bettergi_miniweb.config import get_port

app = create_app()

__all__ = [
    "PostData",
    "app",
    "create_app",
    "db",
    "normalize_webhook_payload",
    "save_webhook_payload",
]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=get_port(), debug=False)
