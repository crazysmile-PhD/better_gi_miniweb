"""Application factory for the Better GI MiniWeb Flask app."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from flask import Flask

from bettergi_miniweb.extensions import db
from bettergi_miniweb.routes import dashboard_bp, health_bp, image_bp, webhook_bp

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URI = f"sqlite:///{BASE_DIR / 'bettergi.db'}"


def configure_logging() -> None:
    """Configure application logging from environment variables."""

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application."""

    configure_logging()

    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=str(BASE_DIR / "static"),
        template_folder=str(BASE_DIR / "templates"),
    )
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URI),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(webhook_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(image_bp)
    return app
