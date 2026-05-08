"""Blueprint exports for Better GI MiniWeb routes."""

from bettergi_miniweb.routes.dashboard import dashboard_bp
from bettergi_miniweb.routes.image import image_bp
from bettergi_miniweb.routes.webhook import webhook_bp

__all__ = ["dashboard_bp", "image_bp", "webhook_bp"]
