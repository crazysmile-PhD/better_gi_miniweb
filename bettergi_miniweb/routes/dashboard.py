"""Dashboard routes."""

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import select

from bettergi_miniweb.extensions import db
from bettergi_miniweb.models import PostData

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def page():
    posts = db.session.scalars(
        select(PostData).order_by(PostData.create_time.desc()).limit(10)
    ).all()
    last_id = min((post.id for post in posts), default=0)
    return render_template("base.html", data=posts, last_id=last_id)


@dashboard_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@dashboard_bp.after_app_request
def add_header(response):
    if request.method == "GET":
        response.cache_control.public = True
        response.cache_control.max_age = 86400
    return response
