"""Image HTTP routes for serving Base64 screenshots stored on PostData."""

import base64
import binascii
from io import BytesIO

from flask import Blueprint, current_app, send_file

from bettergi_miniweb.extensions import db
from bettergi_miniweb.models import PostData

image_bp = Blueprint("image", __name__)


@image_bp.get("/image/<int:image_id>")
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