"""Phase 6 — new tables: organizations, org_members, refresh_tokens, audit_log, consent_records

Revision ID: 001_phase6_new_tables
Revises: (none — first migration)
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "001_phase6_new_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── organizations ──────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("plan_tier", sa.String, nullable=False, server_default="free"),
        sa.Column("recording_retention_days", sa.Integer, nullable=False, server_default="90"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── org_members ────────────────────────────────────────────
    op.create_table(
        "org_members",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("role", sa.String, nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_member"),
    )

    # ── refresh_tokens ─────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("token_hash", sa.String, nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── audit_log ──────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("resource_type", sa.String, nullable=False),
        sa.Column("resource_id", sa.Integer, nullable=True),
        sa.Column("diff_json", sa.JSON, nullable=True),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column("ip_address", sa.String, nullable=True),
    )

    # ── consent_records ────────────────────────────────────────
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data_subject_identifier", sa.String, nullable=False),
        sa.Column("consent_type", sa.String, nullable=False),
        sa.Column("consented_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("consent_source", sa.String, nullable=False),
        sa.Column("withdrawn_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("consent_records")
    op.drop_table("audit_log")
    op.drop_table("refresh_tokens")
    op.drop_table("org_members")
    op.drop_table("organizations")
