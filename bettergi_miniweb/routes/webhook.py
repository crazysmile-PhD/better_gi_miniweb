"""Webhook HTTP routes that validate request shape before calling services."""

from __future__ import annotations

import hashlib
import hmac

from flask import Blueprint, current_app, jsonify, request

from bettergi_miniweb.extensions import db
from bettergi_miniweb.services.webhook_service import save_webhook_payload

webhook_bp = Blueprint("webhook", __name__)


def _configured_token() -> str:
    return str(current_app.config.get("WEBHOOK_TOKEN") or "")


def _configured_signature_secret() -> str:
    return str(current_app.config.get("WEBHOOK_SIGNATURE_SECRET") or "")


def _request_token() -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    return request.headers.get("X-Webhook-Token", "").strip()


def _signature_matches(raw_body: bytes, secret: str) -> bool:
    supplied_signature = request.headers.get("X-Webhook-Signature", "").strip()
    if not supplied_signature:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    accepted_signatures = (expected_signature, f"sha256={expected_signature}")
    return any(hmac.compare_digest(supplied_signature, value) for value in accepted_signatures)


def _webhook_auth_error(raw_body: bytes):
    token = _configured_token()
    if token and not hmac.compare_digest(_request_token(), token):
        return jsonify({"msg": "error", "error": "Invalid webhook token"}), 401

    signature_secret = _configured_signature_secret()
    if signature_secret and not _signature_matches(raw_body, signature_secret):
        return jsonify({"msg": "error", "error": "Invalid webhook signature"}), 401

    return None


@webhook_bp.post("/")
def webhook():
    raw_body = request.get_data(cache=True)
    auth_error = _webhook_auth_error(raw_body)
    if auth_error is not None:
        return auth_error

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
