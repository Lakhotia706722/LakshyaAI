from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db import get_db
from app.models import DealEvent, Deal, EventSource, DealStage
from app.schemas import WhatsAppIntelligenceResponse, DealEventResponse
from app.routers.auth import get_current_user_with_org
from app.services.ai_extraction import AIExtractionService

router = APIRouter()


def _demo_intelligence_stub(text: str) -> dict:
    return {
        "stage": "proposal",
        "summary": (
            "⚠️ Demo result — ANTHROPIC_API_KEY not configured. "
            "Add it to backend/.env to get real AI analysis."
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
    user,
    org_id: int,
) -> dict:
    """Core analysis logic shared by /analyze and /upload endpoints."""

    try:
        ai_service = AIExtractionService()
        intelligence = ai_service.extract_whatsapp_intelligence(conversation_text)
    except ValueError:
        intelligence = _demo_intelligence_stub(conversation_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI extraction error: {str(e)}")

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
            org_id=org_id,
            company_id=new_deal_company_id,
            title=new_deal_title,
            stage=stage_map.get(intelligence["stage"], DealStage.PROSPECTING),
            owner_name=user.name,
            risk_flag=len(intelligence.get("risk_signals", [])) > 0,
            risk_reason=", ".join(
                r["description"] for r in intelligence.get("risk_signals", [])[:2]
            ),
        )
        db.add(new_deal)
        db.commit()
        db.refresh(new_deal)
        target_deal_id = new_deal.id

    deal_event = None
    if target_deal_id:
        # Ensure deal belongs to this org
        deal = db.query(Deal).filter(
            Deal.id == target_deal_id, Deal.org_id == org_id
        ).first()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

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
            org_id=org_id,
            deal_id=target_deal_id,
            source=EventSource.WHATSAPP,
            raw_text=conversation_text,
            extracted_summary=intelligence.get("summary", ""),
            next_step=next_step_text,
            next_step_deadline=next_step_deadline,
        )
        db.add(deal_event)

        if intelligence.get("risk_signals"):
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
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Analyze pasted WhatsApp conversation text."""
    user, org_id, _ = user_org_role
    if not conversation_text.strip():
        raise HTTPException(status_code=400, detail="conversation_text cannot be empty")
    return await _run_analysis(
        conversation_text, deal_id, create_new_deal,
        new_deal_title, new_deal_company_id, db, user, org_id,
    )


@router.post("/upload", response_model=WhatsAppIntelligenceResponse)
async def upload_whatsapp_file(
    file: UploadFile = File(...),
    deal_id: Optional[int] = Form(None),
    create_new_deal: bool = Form(False),
    new_deal_title: Optional[str] = Form(None),
    new_deal_company_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Upload and analyze a WhatsApp export .txt file."""
    user, org_id, _ = user_org_role
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
        new_deal_title, new_deal_company_id, db, user, org_id,
    )


@router.get("/events/{deal_id}", response_model=List[DealEventResponse])
def get_deal_events(
    deal_id: int,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get all WhatsApp intelligence events for a deal (org-scoped)."""
    _, org_id, _ = user_org_role
    # Verify deal belongs to this org
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.org_id == org_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return (
        db.query(DealEvent)
        .filter(DealEvent.deal_id == deal_id, DealEvent.source == EventSource.WHATSAPP)
        .order_by(DealEvent.created_at.desc())
        .all()
    )


@router.get("/webhook/{org_id}")
async def verify_whatsapp_webhook(
    org_id: int,
    hub_mode: str = Depends(lambda mode=None: mode),
    hub_challenge: str = Depends(lambda challenge=None: challenge),
    hub_verify_token: str = Depends(lambda verify_token=None: verify_token)
):
    """WhatsApp webhook verification endpoint."""
    # In a real app, verify the token matches a secure environment variable
    return int(hub_challenge) if hub_challenge else "OK"


@router.post("/webhook/{org_id}")
async def receive_whatsapp_webhook(
    org_id: int,
    payload: dict,
    db: Session = Depends(get_db)
):
    """Receive live messages from WhatsApp Business API."""
    # Extract message text from payload (assuming standard WhatsApp Cloud API format)
    try:
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            return {"status": "ignored", "reason": "no messages"}
            
        message = messages[0]
        message_text = message.get("text", {}).get("body", "")
        phone_number = message.get("from", "")
        
        if not message_text:
             return {"status": "ignored", "reason": "not a text message"}

        # For MVP, we will try to find a deal by this phone number or just create a stub event
        # This is where we'd invoke AIExtractionService in a background task
        # and then CRMSyncService
        
        # Here we mock user context for _run_analysis
        class DummyUser:
            name = f"Webhook User ({phone_number})"
            
        # Simplified async call or background task dispatch would go here.
        # For MVP, we'll invoke _run_analysis directly if we can find/create a deal.
        
        return {"status": "received"}
        
    except (IndexError, KeyError) as e:
        return {"status": "error", "reason": str(e)}
