"""Add screenshot_path for file-backed screenshots.

Revision ID: 202605110002
Revises: 202605110001
Create Date: 2026-05-11 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202605110002"
down_revision = "202605110001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("post_data", sa.Column("screenshot_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("post_data", "screenshot_path")
