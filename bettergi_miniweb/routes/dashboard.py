"""Dashboard HTTP routes for rendering persisted BetterGI events."""

from __future__ import annotations

from datetime import datetime, time, timezone
from math import ceil
from typing import Any

from flask import Blueprint, render_template, request
from sqlalchemy import func, or_, select

from bettergi_miniweb.extensions import db
from bettergi_miniweb.models import PostData

dashboard_bp = Blueprint("dashboard", __name__)

DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100


def _positive_int_arg(name: str, default: int, maximum: int | None = None) -> int:
    raw_value = request.args.get(name, "")
    try:
        value = int(raw_value)
    except ValueError:
        value = default
    value = max(value, 1)
    if maximum is not None:
        value = min(value, maximum)
    return value


def _refresh_arg() -> int:
    raw_value = request.args.get("refresh", "")
    try:
        return max(int(raw_value), 0)
    except ValueError:
        return 0


def _date_arg(name: str, errors: list[str]) -> datetime | None:
    raw_value = request.args.get(name, "").strip()
    if not raw_value:
        return None

    try:
        parsed_date = datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{name} must use YYYY-MM-DD format")
        return None

    if name == "date_to":
        return datetime.combine(parsed_date, time.max, tzinfo=timezone.utc)
    return datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)


def _dashboard_filters() -> tuple[Any, dict[str, Any], list[str]]:
    errors: list[str] = []
    q = request.args.get("q", "").strip()
    result = request.args.get("result", "").strip()
    date_from = _date_arg("date_from", errors)
    date_to = _date_arg("date_to", errors)

    statement = select(PostData)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                PostData.event.ilike(pattern),
                PostData.message.ilike(pattern),
                PostData.result.ilike(pattern),
            )
        )
    if result:
        statement = statement.where(PostData.result == result)
    if date_from is not None:
        statement = statement.where(PostData.create_time >= date_from)
    if date_to is not None:
        statement = statement.where(PostData.create_time <= date_to)

    return statement, {"q": q, "result": result}, errors


@dashboard_bp.get("/")
def page():
    page_number = _positive_int_arg("page", 1)
    per_page = _positive_int_arg("per_page", DEFAULT_PER_PAGE, MAX_PER_PAGE)
    refresh = _refresh_arg()
    statement, filters, filter_errors = _dashboard_filters()

    total = db.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    total_pages = max(ceil(total / per_page), 1)
    page_number = min(page_number, total_pages)
    posts = db.session.scalars(
        statement.order_by(PostData.create_time.desc()).limit(per_page).offset((page_number - 1) * per_page)
    ).all()
    last_id = min((post.id for post in posts), default=0)

    return render_template(
        "dashboard.html",
        data=posts,
        last_id=last_id,
        filters=filters,
        filter_errors=filter_errors,
        pagination={
            "page": page_number,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page_number > 1,
            "has_next": page_number < total_pages,
        },
        refresh=refresh,
    )


@dashboard_bp.after_app_request
def add_header(response):
    if request.method == "GET":
        response.cache_control.public = True
        response.cache_control.max_age = 86400
    return response
