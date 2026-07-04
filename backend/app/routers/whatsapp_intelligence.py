from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import json

from app.db import get_db
from app.models import DealEvent, Deal, User, EventSource
from app.schemas import (
    WhatsAppIntelligenceCreate, 
    WhatsAppIntelligenceResponse,
    DealEventResponse
)
from app.routers.auth import get_current_user
from app.services.ai_extraction import AIExtractionService

router = APIRouter()


@router.post("/analyze", response_model=WhatsAppIntelligenceResponse)
async def analyze_whatsapp_conversation(
    conversation_text: str = Form(...),
    deal_id: Optional[int] = Form(None),
    create_new_deal: bool = Form(False),
    new_deal_title: Optional[str] = Form(None),
    new_deal_company_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze WhatsApp conversation and extract deal intelligence.
    
    Can either:
    1. Link to existing deal (provide deal_id)
    2. Create new deal (set create_new_deal=True with new_deal_title and new_deal_company_id)
    3. Just analyze without saving (don't provide deal_id or create_new_deal)
    """
    
    try:
        # Initialize AI extraction service
        ai_service = AIExtractionService()
        
        # Extract intelligence from conversation
        intelligence = ai_service.extract_whatsapp_intelligence(conversation_text)
        
        # Handle deal creation or linking
        target_deal_id = deal_id
        
        if create_new_deal and new_deal_title and new_deal_company_id:
            # Create new deal
            from app.models import DealStage
            
            # Map extracted stage to DealStage enum
            stage_map = {
                "prospecting": DealStage.PROSPECTING,
                "demo": DealStage.DEMO,
                "proposal": DealStage.PROPOSAL,
                "negotiation": DealStage.NEGOTIATION,
                "closed_won": DealStage.CLOSED_WON,
                "closed_lost": DealStage.CLOSED_LOST
            }
            
            new_deal = Deal(
                company_id=new_deal_company_id,
                title=new_deal_title,
                stage=stage_map.get(intelligence["stage"], DealStage.PROSPECTING),
                owner_name=current_user.name,
                risk_flag=len(intelligence.get("risk_signals", [])) > 0,
                risk_reason=", ".join([r["description"] for r in intelligence.get("risk_signals", [])[:2]])
            )
            db.add(new_deal)
            db.commit()
            db.refresh(new_deal)
            target_deal_id = new_deal.id
        
        # Save as deal event if we have a deal
        deal_event = None
        if target_deal_id:
            # Calculate next step deadline from next_steps
            next_step_text = None
            next_step_deadline = None
            
            if intelligence.get("next_steps"):
                # Get the highest priority next step
                sorted_steps = sorted(
                    intelligence["next_steps"],
                    key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "low"), 2)
                )
                if sorted_steps:
                    top_step = sorted_steps[0]
                    next_step_text = f"{top_step.get('action')} (Owner: {top_step.get('owner', 'Unassigned')})"
                    
                    # Parse deadline if present
                    if top_step.get("deadline"):
                        try:
                            next_step_deadline = datetime.strptime(top_step["deadline"], "%Y-%m-%d").date()
                        except:
                            pass
            
            deal_event = DealEvent(
                deal_id=target_deal_id,
                source=EventSource.WHATSAPP,
                raw_text=conversation_text,
                extracted_summary=intelligence.get("summary", ""),
                next_step=next_step_text,
                next_step_deadline=next_step_deadline
            )
            db.add(deal_event)
            
            # Update deal with risk information if needed
            if intelligence.get("risk_signals"):
                deal = db.query(Deal).filter(Deal.id == target_deal_id).first()
                if deal:
                    deal.risk_flag = True
                    high_risks = [r for r in intelligence["risk_signals"] if r.get("severity") == "high"]
                    if high_risks:
                        deal.risk_reason = high_risks[0]["description"]
            
            db.commit()
            if deal_event:
                db.refresh(deal_event)
        
        # Build response
        response = {
            "intelligence": intelligence,
            "deal_event_id": deal_event.id if deal_event else None,
            "deal_id": target_deal_id,
            "conversation_text": conversation_text[:500] + "..." if len(conversation_text) > 500 else conversation_text
        }
        
        return response
        
    except ValueError as e:
        # API key not configured
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service not configured: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing conversation: {str(e)}"
        )


@router.post("/upload", response_model=WhatsAppIntelligenceResponse)
async def upload_whatsapp_file(
    file: UploadFile = File(...),
    deal_id: Optional[int] = Form(None),
    create_new_deal: bool = Form(False),
    new_deal_title: Optional[str] = Form(None),
    new_deal_company_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and analyze WhatsApp export file (.txt)
    """
    
    # Validate file type
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt files are supported"
        )
    
    # Read file content
    content = await file.read()
    conversation_text = content.decode('utf-8')
    
    # Reuse the analyze endpoint logic
    return await analyze_whatsapp_conversation(
        conversation_text=conversation_text,
        deal_id=deal_id,
        create_new_deal=create_new_deal,
        new_deal_title=new_deal_title,
        new_deal_company_id=new_deal_company_id,
        db=db,
        current_user=current_user
    )


@router.get("/events/{deal_id}", response_model=List[DealEventResponse])
def get_deal_events(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all WhatsApp intelligence events for a deal"""
    
    events = db.query(DealEvent).filter(
        DealEvent.deal_id == deal_id,
        DealEvent.source == EventSource.WHATSAPP
    ).order_by(DealEvent.created_at.desc()).all()
    
    return events
