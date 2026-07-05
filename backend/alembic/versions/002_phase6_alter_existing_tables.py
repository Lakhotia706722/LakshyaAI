"""Phase 6 — alter existing tables: add org_id FK and new user columns

Revision ID: 002_phase6_alter_existing_tables
Revises: 001_phase6_new_tables
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "002_phase6_alter_existing_tables"
down_revision = "001_phase6_new_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users: new columns ─────────────────────────────────────
    op.add_column("users", sa.Column("is_email_verified", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("email_verification_token", sa.String, nullable=True))
    op.add_column("users", sa.Column("password_reset_token", sa.String, nullable=True))
    op.add_column("users", sa.Column("password_reset_expires", sa.DateTime, nullable=True))
    op.add_column("users", sa.Column("provider", sa.String, nullable=True))

    # Make password_hash nullable for future OAuth users
    # SQLite doesn't support ALTER COLUMN — handle via batch mode
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("password_hash", nullable=True)

    # ── companies: add org_id ──────────────────────────────────
    op.add_column("companies", sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_companies_org_id", "companies", ["org_id"])

    # ── deals: add org_id ─────────────────────────────────────
    op.add_column("deals", sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_deals_org_id", "deals", ["org_id"])

    # ── deal_events: add org_id ────────────────────────────────
    op.add_column("deal_events", sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_deal_events_org_id", "deal_events", ["org_id"])

    # ── call_recordings: add org_id + storage_type ────────────
    op.add_column("call_recordings", sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True))
    op.add_column("call_recordings", sa.Column("storage_type", sa.String, nullable=False, server_default="local"))
    op.create_index("ix_call_recordings_org_id", "call_recordings", ["org_id"])

    # ── invoices: add org_id ───────────────────────────────────
    op.add_column("invoices", sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_invoices_org_id", "invoices", ["org_id"])

    # ── forecast_snapshots: add org_id ────────────────────────
    op.add_column("forecast_snapshots", sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_forecast_snapshots_org_id", "forecast_snapshots", ["org_id"])


def downgrade() -> None:
    # forecast_snapshots
    op.drop_index("ix_forecast_snapshots_org_id", "forecast_snapshots")
    op.drop_column("forecast_snapshots", "org_id")

    # invoices
    op.drop_index("ix_invoices_org_id", "invoices")
    op.drop_column("invoices", "org_id")

    # call_recordings
    op.drop_index("ix_call_recordings_org_id", "call_recordings")
    op.drop_column("call_recordings", "storage_type")
    op.drop_column("call_recordings", "org_id")

    # deal_events
    op.drop_index("ix_deal_events_org_id", "deal_events")
    op.drop_column("deal_events", "org_id")

    # deals
    op.drop_index("ix_deals_org_id", "deals")
    op.drop_column("deals", "org_id")

    # companies
    op.drop_index("ix_companies_org_id", "companies")
    op.drop_column("companies", "org_id")

    # users
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("password_hash", nullable=False)
    op.drop_column("users", "provider")
    op.drop_column("users", "password_reset_expires")
    op.drop_column("users", "password_reset_token")
    op.drop_column("users", "email_verification_token")
    op.drop_column("users", "is_email_verified")
