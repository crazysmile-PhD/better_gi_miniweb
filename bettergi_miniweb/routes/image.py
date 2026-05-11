"""Image HTTP routes for serving screenshots stored on PostData."""

import base64
import binascii
from io import BytesIO

from flask import Blueprint, current_app, send_file

from bettergi_miniweb.extensions import db
from bettergi_miniweb.models import PostData
from bettergi_miniweb.services.webhook_service import resolve_screenshot_path

image_bp = Blueprint("image", __name__)


@image_bp.get("/image/<int:image_id>")
def serve_image(image_id: int):
    post = db.session.get(PostData, image_id)
    if post is None:
        return "Image not found", 404

    if post.screenshot_path:
        screenshot_path = resolve_screenshot_path(post.screenshot_path)
        if screenshot_path is None:
            return "Image not found", 404
        if screenshot_path.is_file():
            return send_file(screenshot_path, mimetype="image/png")

    if not post.screenshot:
        return "Image not found", 404

    try:
        binary_data = base64.b64decode(post.screenshot, validate=True)
    except (binascii.Error, ValueError):
        current_app.logger.warning("Invalid screenshot data for post %s", image_id)
        return "Invalid image data", 422

    img_io = BytesIO(binary_data)
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")
