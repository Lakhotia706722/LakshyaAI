from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Date, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db import Base


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


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    industry = Column(String)
    city = Column(String)
    state = Column(String)
    employee_band = Column(String)  # e.g., "50-200", "200-500"
    gst_number = Column(String)
    udyam_number = Column(String)
    financial_health_score = Column(Integer)  # 0-100
    growth_signal = Column(Integer)  # 0-100
    tech_stack_tags = Column(JSON)  # List of tech tags
    source = Column(String, default="seed_data")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    deals = relationship("Deal", back_populates="company")
    invoices = relationship("Invoice", back_populates="company")


class Deal(Base):
    __tablename__ = "deals"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title = Column(String, nullable=False)
    stage = Column(SQLEnum(DealStage), nullable=False, default=DealStage.PROSPECTING)
    value_inr = Column(Integer)  # Deal value in INR
    owner_name = Column(String)
    sentiment_trend = Column(JSON)  # Array of {date, score}
    risk_flag = Column(Boolean, default=False)
    risk_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="deals")
    events = relationship("DealEvent", back_populates="deal")
    call_recordings = relationship("CallRecording", back_populates="deal")
    invoices = relationship("Invoice", back_populates="deal")


class DealEvent(Base):
    __tablename__ = "deal_events"
    
    id = Column(Integer, primary_key=True, index=True)
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
    deal_id = Column(Integer, ForeignKey("deals.id"))
    file_path = Column(String, nullable=False)
    language = Column(String)
    transcript = Column(Text)
    analysis_json = Column(JSON)  # {talk_time_ratio, objections, competitor_mentions, coaching_notes}
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    deal = relationship("Deal", back_populates="call_recordings")


class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    amount_inr = Column(Integer, nullable=False)
    invoice_date = Column(Date, nullable=False)
    status = Column(String)  # e.g., "paid", "pending", "overdue"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="invoices")
    deal = relationship("Deal", back_populates="invoices")


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    pipeline_value_inr = Column(Integer)
    invoiced_value_inr = Column(Integer)
    gap_pct = Column(Integer)  # Percentage gap
    notes = Column(Text)
