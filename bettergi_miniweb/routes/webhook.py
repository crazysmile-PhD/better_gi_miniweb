"""Webhook HTTP routes that validate request shape before calling services."""

from flask import Blueprint, current_app, jsonify, request

from bettergi_miniweb.extensions import db
from bettergi_miniweb.services.webhook_service import save_webhook_payload

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.post("/")
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
