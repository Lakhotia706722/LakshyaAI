from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Boolean,
    Date, JSON, Enum as SQLEnum, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db import Base


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class DealStage(str, enum.Enum):
    PROSPECTING = "prospecting"
    DEMO = "demo"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class EventSource(str, enum.Enum):
    WHATSAPP = "whatsapp"
    CALL = "call"
    MANUAL = "manual"


class OrgRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class ConsentType(str, enum.Enum):
    CALL_RECORDING = "call_recording"
    WHATSAPP_PROCESSING = "whatsapp_processing"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# ─────────────────────────────────────────────────────────────
# Organizations
# ─────────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plan_tier = Column(String, default="free", nullable=False)
    recording_retention_days = Column(Integer, default=90, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    members = relationship("OrgMember", back_populates="organization")
    companies = relationship("Company", back_populates="organization")
    deals = relationship("Deal", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")
    consent_records = relationship("ConsentRecord", back_populates="organization")


class OrgMember(Base):
    __tablename__ = "org_members"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(SQLEnum(OrgRole), nullable=False, default=OrgRole.MEMBER)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_member"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="org_memberships")


# ─────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # Nullable to support future OAuth users who have no password
    password_hash = Column(String, nullable=True)
    name = Column(String, nullable=False)
    # Email verification
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String, nullable=True)
    # Password reset
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    # OAuth support stub
    provider = Column(String, nullable=True)   # None = email/password, "google" = OAuth
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    org_memberships = relationship("OrgMember", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    consent_records = relationship("ConsentRecord", back_populates="user")


# ─────────────────────────────────────────────────────────────
# Auth tokens
# ─────────────────────────────────────────────────────────────

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


# ─────────────────────────────────────────────────────────────
# Core business models — all scoped by org_id
# ─────────────────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    industry = Column(String)
    city = Column(String)
    state = Column(String)
    employee_band = Column(String)
    gst_number = Column(String)
    udyam_number = Column(String)
    financial_health_score = Column(Integer)   # 0-100
    growth_signal = Column(Integer)            # 0-100
    tech_stack_tags = Column(JSON)
    source = Column(String, default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="companies")
    deals = relationship("Deal", back_populates="company")
    invoices = relationship("Invoice", back_populates="company")


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title = Column(String, nullable=False)
    stage = Column(SQLEnum(DealStage), nullable=False, default=DealStage.PROSPECTING)
    value_inr = Column(Integer)
    owner_name = Column(String)
    sentiment_trend = Column(JSON)
    risk_flag = Column(Boolean, default=False)
    risk_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="deals")
    company = relationship("Company", back_populates="deals")
    events = relationship("DealEvent", back_populates="deal")
    call_recordings = relationship("CallRecording", back_populates="deal")
    invoices = relationship("Invoice", back_populates="deal")


class DealEvent(Base):
    __tablename__ = "deal_events"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    source = Column(SQLEnum(EventSource), nullable=False)
    raw_text = Column(Text)
    extracted_summary = Column(Text)
    next_step = Column(Text)
    next_step_deadline = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    deal = relationship("Deal", back_populates="events")


class CallRecording(Base):
    __tablename__ = "call_recordings"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    file_path = Column(String, nullable=False)   # local path or S3 key
    storage_type = Column(String, default="local")  # "local" or "s3"
    language = Column(String)
    transcript = Column(Text)
    analysis_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    deal = relationship("Deal", back_populates="call_recordings")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    amount_inr = Column(Integer, nullable=False)
    invoice_date = Column(Date, nullable=False)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="invoices")
    deal = relationship("Deal", back_populates="invoices")


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    pipeline_value_inr = Column(Integer)
    invoiced_value_inr = Column(Integer)
    gap_pct = Column(Integer)
    notes = Column(Text)


# ─────────────────────────────────────────────────────────────
# Audit log (append-only)
# ─────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(SQLEnum(AuditAction), nullable=False)
    resource_type = Column(String, nullable=False)   # "deal", "company", etc.
    resource_id = Column(Integer, nullable=True)
    diff_json = Column(JSON, nullable=True)          # before/after for updates
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")


# ─────────────────────────────────────────────────────────────
# DPDP compliance
# ─────────────────────────────────────────────────────────────

class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # The third-party contact whose data is being processed
    data_subject_identifier = Column(String, nullable=False)
    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    consented_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    consent_source = Column(String, nullable=False)  # "verbal_on_call", "whatsapp_opt_in"
    withdrawn_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="consent_records")
    user = relationship("User", back_populates="consent_records")
