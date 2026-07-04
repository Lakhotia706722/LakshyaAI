from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.models import Deal, User
from app.schemas import DealCreate, DealResponse, DealUpdate, DashboardStats
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[DealResponse])
def get_deals(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all deals"""
    deals = db.query(Deal).offset(skip).limit(limit).all()
    return deals


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics"""
    from app.models import Company, DealStage
    from sqlalchemy import func
    
    # Total pipeline value
    total_pipeline = db.query(func.sum(Deal.value_inr)).filter(
        Deal.stage.notin_([DealStage.CLOSED_LOST])
    ).scalar() or 0
    
    # Deals by stage
    deals_by_stage = {}
    for stage in DealStage:
        count = db.query(func.count(Deal.id)).filter(Deal.stage == stage).scalar()
        deals_by_stage[stage.value] = count
    
    # Risk flagged deals
    risk_flagged = db.query(func.count(Deal.id)).filter(Deal.risk_flag == True).scalar()
    
    # Top companies by growth signal
    top_companies = db.query(Company).order_by(
        Company.growth_signal.desc().nullslast()
    ).limit(5).all()
    
    return {
        "total_pipeline_value": total_pipeline,
        "deals_by_stage": deals_by_stage,
        "risk_flagged_deals": risk_flagged,
        "forecast_gap_pct": None,  # Will be populated in Phase 4
        "top_companies": top_companies
    }


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific deal"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )
    return deal


@router.post("/", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    deal: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new deal"""
    db_deal = Deal(**deal.model_dump())
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    return db_deal


@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int,
    deal_update: DealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a deal"""
    db_deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not db_deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )
    
    # Update only provided fields
    for field, value in deal_update.model_dump(exclude_unset=True).items():
        setattr(db_deal, field, value)
    
    db.commit()
    db.refresh(db_deal)
    return db_deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a deal"""
    db_deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not db_deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )
    
    db.delete(db_deal)
    db.commit()
    return None
