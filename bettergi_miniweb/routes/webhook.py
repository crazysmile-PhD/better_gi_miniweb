"""Webhook HTTP routes that validate request shape before calling services."""

from __future__ import annotations

import hmac
from hashlib import sha256

from flask import Blueprint, current_app, jsonify, request

from bettergi_miniweb.extensions import db
from bettergi_miniweb.services.webhook_service import save_webhook_payload

webhook_bp = Blueprint("webhook", __name__)


def _expected_signature(raw_body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_body, sha256).hexdigest()
    return f"sha256={digest}"


def _request_token() -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("X-Webhook-Token")


def _verify_webhook_auth(raw_body: bytes) -> tuple[bool, str | None]:
    token = current_app.config.get("WEBHOOK_TOKEN")
    signature_secret = current_app.config.get("WEBHOOK_SIGNATURE_SECRET")

    if token and not hmac.compare_digest(str(token), _request_token() or ""):
        return False, "Invalid webhook token"

    if signature_secret:
        supplied_signature = request.headers.get("X-Webhook-Signature", "")
        expected_signature = _expected_signature(raw_body, str(signature_secret))
        if not hmac.compare_digest(expected_signature, supplied_signature):
            return False, "Invalid webhook signature"

    return True, None


@webhook_bp.post("/")
def webhook():
    raw_body = request.get_data(cache=True)
    is_authorized, auth_error = _verify_webhook_auth(raw_body)
    if not is_authorized:
        return jsonify({"msg": "error", "error": auth_error}), 401

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
