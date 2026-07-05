from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from app.models import DealStage, EventSource, OrgRole, AuditAction, ConsentType


# ─────────────────────────────────────────────────────────────
# Organization Schemas
# ─────────────────────────────────────────────────────────────

class OrgCreate(BaseModel):
    """Embedded in UserCreate — org is created alongside the first user."""
    name: str


class OrgResponse(BaseModel):
    id: int
    name: str
    plan_tier: str
    recording_retention_days: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrgMemberResponse(BaseModel):
    id: int
    user_id: int
    role: OrgRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# User Schemas
# ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    org_name: str   # Name of the organization to create


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_email_verified: bool
    provider: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    is_email_verified: bool


class TokenData(BaseModel):
    user_id: Optional[int] = None
    org_id: Optional[int] = None
    role: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Company Schemas
# ─────────────────────────────────────────────────────────────

class CompanyBase(BaseModel):
    name: str
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    employee_band: Optional[str] = None
    gst_number: Optional[str] = None
    udyam_number: Optional[str] = None
    financial_health_score: Optional[int] = None
    growth_signal: Optional[int] = None
    tech_stack_tags: Optional[List[str]] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int
    org_id: int
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# Deal Schemas
# ─────────────────────────────────────────────────────────────

class DealBase(BaseModel):
    title: str
    stage: DealStage
    value_inr: Optional[int] = None
    owner_name: Optional[str] = None


class DealCreate(DealBase):
    company_id: int


class DealUpdate(BaseModel):
    title: Optional[str] = None
    stage: Optional[DealStage] = None
    value_inr: Optional[int] = None
    owner_name: Optional[str] = None
    risk_flag: Optional[bool] = None
    risk_reason: Optional[str] = None
    sentiment_trend: Optional[List[Dict[str, Any]]] = None


class DealResponse(DealBase):
    id: int
    org_id: int
    company_id: int
    risk_flag: bool
    risk_reason: Optional[str]
    sentiment_trend: Optional[List[Dict[str, Any]]]
    created_at: datetime
    updated_at: datetime
    company: Optional[CompanyResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# Deal Event Schemas
# ─────────────────────────────────────────────────────────────

class DealEventCreate(BaseModel):
    deal_id: int
    source: EventSource
    raw_text: str


class DealEventResponse(BaseModel):
    id: int
    deal_id: int
    source: EventSource
    raw_text: str
    extracted_summary: Optional[str]
    next_step: Optional[str]
    next_step_deadline: Optional[date]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# WhatsApp Intelligence Schemas
# ─────────────────────────────────────────────────────────────

class WhatsAppIntelligenceCreate(BaseModel):
    conversation_text: str
    deal_id: Optional[int] = None
    create_new_deal: bool = False
    new_deal_title: Optional[str] = None
    new_deal_company_id: Optional[int] = None


class WhatsAppIntelligenceResponse(BaseModel):
    intelligence: Dict[str, Any]
    deal_event_id: Optional[int] = None
    deal_id: Optional[int] = None
    conversation_text: str


# ─────────────────────────────────────────────────────────────
# Call Recording Schemas
# ─────────────────────────────────────────────────────────────

class CallRecordingCreate(BaseModel):
    deal_id: Optional[int] = None
    language: str


class CallRecordingResponse(BaseModel):
    id: int
    org_id: int
    deal_id: Optional[int]
    file_path: str
    storage_type: str
    language: str
    transcript: Optional[str]
    analysis_json: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# Invoice Schemas
# ─────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    company_id: int
    deal_id: Optional[int] = None
    amount_inr: int
    invoice_date: date
    status: str


class InvoiceResponse(InvoiceCreate):
    id: int
    org_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# Forecast Schemas
# ─────────────────────────────────────────────────────────────

class ForecastSnapshotResponse(BaseModel):
    id: int
    org_id: int
    generated_at: datetime
    pipeline_value_inr: int
    invoiced_value_inr: int
    gap_pct: int
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# Dashboard Schemas
# ─────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_pipeline_value: int
    deals_by_stage: Dict[str, int]
    risk_flagged_deals: int
    forecast_gap_pct: Optional[int]
    top_companies: List[CompanyResponse]


# ─────────────────────────────────────────────────────────────
# Audit Log Schemas
# ─────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: int
    org_id: int
    user_id: int
    action: AuditAction
    resource_type: str
    resource_id: Optional[int]
    diff_json: Optional[Dict[str, Any]]
    timestamp: datetime
    ip_address: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# Consent Record Schemas
# ─────────────────────────────────────────────────────────────

class ConsentRecordCreate(BaseModel):
    data_subject_identifier: str
    consent_type: ConsentType
    consent_source: str


class ConsentRecordResponse(ConsentRecordCreate):
    id: int
    org_id: int
    user_id: int
    consented_at: datetime
    withdrawn_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
