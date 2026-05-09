"""Configuration helpers for Better GI MiniWeb."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URI = f"sqlite:///{BASE_DIR / 'bettergi.db'}"
DEFAULT_PORT = 222


def get_log_level() -> str:
    """Return the configured logging level name."""

    return os.getenv("LOG_LEVEL", "INFO")


def get_port() -> int:
    """Return the configured application port."""

    return int(os.getenv("PORT", str(DEFAULT_PORT)))


def get_app_config() -> dict[str, Any]:
    """Return default Flask config before create_app applies test overrides."""

    return {
        "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", DEFAULT_DATABASE_URI),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JSON_SORT_KEYS": False,
        "WEBHOOK_TOKEN": os.getenv("WEBHOOK_TOKEN"),
        "WEBHOOK_SIGNATURE_SECRET": os.getenv("WEBHOOK_SIGNATURE_SECRET"),
    }
