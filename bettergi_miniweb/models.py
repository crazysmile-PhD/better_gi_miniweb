"""Database models for Better GI MiniWeb."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column

from bettergi_miniweb.extensions import db


class PostData(db.Model):
    """A BetterGI webhook event persisted with the existing SQLite schema."""

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
