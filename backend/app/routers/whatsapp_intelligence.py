from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db import get_db
from app.models import DealEvent, Deal, User, EventSource, DealStage
from app.schemas import WhatsAppIntelligenceResponse, DealEventResponse
from app.routers.auth import get_current_user
from app.services.ai_extraction import AIExtractionService

router = APIRouter()


def _demo_intelligence_stub(text: str) -> dict:
    """
    Fallback stub returned when ANTHROPIC_API_KEY is not configured.
    Lets the UI show a realistic-looking demo result so the interface
    is still presentable without live AI.
    """
    return {
        "stage": "proposal",
        "summary": (
            "⚠️ Demo result — ANTHROPIC_API_KEY not configured. "
            "Add it to backend/.env to get real AI analysis. "
            "This stub shows what the output structure looks like."
        ),
        "next_steps": [
            {"action": "Send pricing proposal", "owner": "Sales Rep", "deadline": None, "priority": "high"},
            {"action": "Schedule follow-up call", "owner": "Sales Rep", "deadline": None, "priority": "medium"},
        ],
        "risk_signals": [
            {"type": "price_objection", "description": "Budget concern raised by prospect", "severity": "medium"},
        ],
        "sentiment_trajectory": [
            {"timestamp": "beginning", "score": 0.3, "reason": "Neutral opening"},
            {"timestamp": "middle", "score": -0.1, "reason": "Price concern"},
            {"timestamp": "end", "score": 0.5, "reason": "Demo agreed"},
        ],
        "competitor_mentions": ["Salesforce"],
        "objections": ["Price is higher than current solution", "Needs CFO approval"],
        "key_insights": [
            "Prospect is actively evaluating alternatives",
            "Budget is the primary obstacle",
            "Demo scheduled — strong buying signal",
        ],
        "_demo_mode": True,
    }


async def _run_analysis(
    conversation_text: str,
    deal_id: Optional[int],
    create_new_deal: bool,
    new_deal_title: Optional[str],
    new_deal_company_id: Optional[int],
    db: Session,
    current_user: User,
) -> dict:
    """Core analysis logic shared by /analyze and /upload endpoints."""

    # --- AI extraction (graceful fallback when key not set) ---
    try:
        ai_service = AIExtractionService()
        intelligence = ai_service.extract_whatsapp_intelligence(conversation_text)
    except ValueError:
        intelligence = _demo_intelligence_stub(conversation_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI extraction error: {str(e)}"
        )

    # --- Deal creation ---
    target_deal_id = deal_id
    if create_new_deal and new_deal_title and new_deal_company_id:
        stage_map = {
            "prospecting": DealStage.PROSPECTING,
            "demo": DealStage.DEMO,
            "proposal": DealStage.PROPOSAL,
            "negotiation": DealStage.NEGOTIATION,
            "closed_won": DealStage.CLOSED_WON,
            "closed_lost": DealStage.CLOSED_LOST,
        }
        new_deal = Deal(
            company_id=new_deal_company_id,
            title=new_deal_title,
            stage=stage_map.get(intelligence["stage"], DealStage.PROSPECTING),
            owner_name=current_user.name,
            risk_flag=len(intelligence.get("risk_signals", [])) > 0,
            risk_reason=", ".join(
                r["description"] for r in intelligence.get("risk_signals", [])[:2]
            ),
        )
        db.add(new_deal)
        db.commit()
        db.refresh(new_deal)
        target_deal_id = new_deal.id

    # --- Save deal event ---
    deal_event = None
    if target_deal_id:
        next_step_text = None
        next_step_deadline = None

        steps = intelligence.get("next_steps", [])
        if steps:
            top = sorted(steps, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "low"), 2))[0]
            next_step_text = f"{top.get('action')} (Owner: {top.get('owner', 'Unassigned')})"
            if top.get("deadline"):
                try:
                    next_step_deadline = datetime.strptime(top["deadline"], "%Y-%m-%d").date()
                except Exception:
                    pass

        deal_event = DealEvent(
            deal_id=target_deal_id,
            source=EventSource.WHATSAPP,
            raw_text=conversation_text,
            extracted_summary=intelligence.get("summary", ""),
            next_step=next_step_text,
            next_step_deadline=next_step_deadline,
        )
        db.add(deal_event)

        # Update deal risk flag
        if intelligence.get("risk_signals"):
            deal = db.query(Deal).filter(Deal.id == target_deal_id).first()
            if deal:
                deal.risk_flag = True
                high = [r for r in intelligence["risk_signals"] if r.get("severity") == "high"]
                if high:
                    deal.risk_reason = high[0]["description"]

        db.commit()
        db.refresh(deal_event)

    return {
        "intelligence": intelligence,
        "deal_event_id": deal_event.id if deal_event else None,
        "deal_id": target_deal_id,
        "conversation_text": (
            conversation_text[:500] + "..." if len(conversation_text) > 500 else conversation_text
        ),
    }


@router.post("/analyze", response_model=WhatsAppIntelligenceResponse)
async def analyze_whatsapp_conversation(
    conversation_text: str = Form(...),
    deal_id: Optional[int] = Form(None),
    create_new_deal: bool = Form(False),
    new_deal_title: Optional[str] = Form(None),
    new_deal_company_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze pasted WhatsApp conversation text."""
    if not conversation_text.strip():
        raise HTTPException(status_code=400, detail="conversation_text cannot be empty")

    return await _run_analysis(
        conversation_text, deal_id, create_new_deal,
        new_deal_title, new_deal_company_id, db, current_user
    )


@router.post("/upload", response_model=WhatsAppIntelligenceResponse)
async def upload_whatsapp_file(
    file: UploadFile = File(...),
    deal_id: Optional[int] = Form(None),
    create_new_deal: bool = Form(False),
    new_deal_title: Optional[str] = Form(None),
    new_deal_company_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and analyze a WhatsApp export .txt file."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    content = await file.read()
    try:
        conversation_text = content.decode("utf-8")
    except UnicodeDecodeError:
        conversation_text = content.decode("utf-8", errors="replace")

    if not conversation_text.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    return await _run_analysis(
        conversation_text, deal_id, create_new_deal,
        new_deal_title, new_deal_company_id, db, current_user
    )


@router.get("/events/{deal_id}", response_model=List[DealEventResponse])
def get_deal_events(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all WhatsApp intelligence events for a deal."""
    return (
        db.query(DealEvent)
        .filter(DealEvent.deal_id == deal_id, DealEvent.source == EventSource.WHATSAPP)
        .order_by(DealEvent.created_at.desc())
        .all()
    )
