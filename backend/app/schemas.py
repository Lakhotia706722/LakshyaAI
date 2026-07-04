from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from app.models import DealStage, EventSource


# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# Company Schemas
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
    source: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Deal Schemas
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
    company_id: int
    risk_flag: bool
    risk_reason: Optional[str]
    sentiment_trend: Optional[List[Dict[str, Any]]]
    created_at: datetime
    updated_at: datetime
    company: Optional[CompanyResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


# Deal Event Schemas
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


# WhatsApp Intelligence Schemas
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


# Call Recording Schemas
class CallRecordingCreate(BaseModel):
    deal_id: Optional[int] = None
    language: str


class CallRecordingResponse(BaseModel):
    id: int
    deal_id: Optional[int]
    file_path: str
    language: str
    transcript: Optional[str]
    analysis_json: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Invoice Schemas
class InvoiceCreate(BaseModel):
    company_id: int
    deal_id: Optional[int] = None
    amount_inr: int
    invoice_date: date
    status: str


class InvoiceResponse(InvoiceCreate):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Forecast Schemas
class ForecastSnapshotResponse(BaseModel):
    id: int
    generated_at: datetime
    pipeline_value_inr: int
    invoiced_value_inr: int
    gap_pct: int
    notes: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


# Dashboard Stats Schema
class DashboardStats(BaseModel):
    total_pipeline_value: int
    deals_by_stage: Dict[str, int]
    risk_flagged_deals: int
    forecast_gap_pct: Optional[int]
    top_companies: List[CompanyResponse]
