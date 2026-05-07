"""Flask application for receiving BetterGI webhooks and displaying them."""

from __future__ import annotations

import base64
import binascii
import logging
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from flask import Flask, current_app, jsonify, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URI = f"sqlite:///{BASE_DIR / 'bettergi.db'}"
WEBHOOK_FIELDS = ("result", "timestamp", "message", "screenshot")


db = SQLAlchemy()


class PostData(db.Model):
    """A BetterGI webhook event persisted in SQLite."""

    __tablename__ = "post_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(db.Text, nullable=False)
    result: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    timestamp: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    screenshot: Mapped[str | None] = mapped_column(db.Text, nullable=True, default=None)
    create_time: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(db.Text, nullable=True)


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__, instance_relative_config=True)
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

    register_routes(app)
    return app


def normalize_webhook_payload(payload: dict[str, Any]) -> dict[str, str | None]:
    """Validate and normalize a BetterGI webhook payload."""

    event = payload.get("event")
    if not isinstance(event, str) or not event.strip():
        raise ValueError("Webhook payload must include a non-empty string field: event")

    normalized: dict[str, str | None] = {"event": event.strip()}
    for field in WEBHOOK_FIELDS:
        value = payload.get(field)
        normalized[field] = None if value is None else str(value)
    return normalized


def save_webhook_payload(payload: dict[str, Any]) -> PostData:
    """Persist one BetterGI webhook payload in SQLite."""

    normalized = normalize_webhook_payload(payload)
    record = PostData(**normalized)
    db.session.add(record)
    db.session.commit()
    return record


def register_routes(app: Flask) -> None:
    """Register web dashboard, webhook, and image routes."""

    @app.post("/")
    def webhook():
        if not request.is_json:
            return jsonify({"msg": "error", "error": "Expected application/json"}), 400

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"msg": "error", "error": "Invalid JSON object"}), 400

        try:
            record = save_webhook_payload(payload)
        except ValueError as exc:
            return jsonify({"msg": "error", "error": str(exc)}), 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Failed to persist webhook payload")
            return jsonify({"msg": "error", "error": "Unable to save payload"}), 500

        return jsonify({"msg": "OK", "id": record.id}), 201

    @app.get("/")
    def page():
        posts = db.session.scalars(
            select(PostData).order_by(PostData.create_time.desc()).limit(10)
        ).all()
        last_id = min((post.id for post in posts), default=0)
        return render_template("base.html", data=posts, last_id=last_id)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/image/<int:image_id>")
    def serve_image(image_id: int):
        post = db.session.get(PostData, image_id)
        if post is None or not post.screenshot:
            return "Image not found", 404

        try:
            binary_data = base64.b64decode(post.screenshot, validate=True)
        except (binascii.Error, ValueError):
            current_app.logger.warning("Invalid screenshot data for post %s", image_id)
            return "Invalid image data", 422

        img_io = BytesIO(binary_data)
        img_io.seek(0)
        return send_file(img_io, mimetype="image/png")

    @app.after_request
    def add_header(response):
        if request.method == "GET":
            response.cache_control.public = True
            response.cache_control.max_age = 86400
        return response


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "222")), debug=False)
