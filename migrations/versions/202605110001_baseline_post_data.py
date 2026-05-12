"""Baseline post_data schema.

Revision ID: 202605110001
Revises: 
Create Date: 2026-05-11 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202605110001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "post_data",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.Text(), nullable=True),
        sa.Column("screenshot", sa.Text(), nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("post_data")
