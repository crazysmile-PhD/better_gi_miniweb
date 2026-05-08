"""Application factory for the Better GI MiniWeb Flask app."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask

from bettergi_miniweb.config import BASE_DIR, get_app_config, get_log_level
from bettergi_miniweb.extensions import db
from bettergi_miniweb.routes import dashboard_bp, health_bp, image_bp, webhook_bp


def configure_logging() -> None:
    """Apply logging configuration before the Flask app starts handling requests."""

    logging.basicConfig(level=get_log_level())


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Build the Flask app, apply config, initialize extensions, and register blueprints."""

    configure_logging()

    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=str(BASE_DIR / "static"),
        template_folder=str(BASE_DIR / "templates"),
    )
    app.config.from_mapping(get_app_config())

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
