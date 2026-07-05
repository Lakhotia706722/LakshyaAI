from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.models import AuditAction, Deal, DealStage, User
from app.schemas import DealCreate, DealResponse, DealUpdate, DashboardStats
from app.routers.auth import (
    get_current_user_with_org,
    require_role,
    write_audit_log,
    OrgRole,
)

router = APIRouter()


@router.get("/", response_model=List[DealResponse])
def get_deals(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get all deals for the current org."""
    _, org_id, _ = user_org_role
    return db.query(Deal).filter(Deal.org_id == org_id).offset(skip).limit(limit).all()


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get dashboard statistics scoped to the current org."""
    from app.models import Company
    from sqlalchemy import func

    _, org_id, _ = user_org_role

    total_pipeline = db.query(func.sum(Deal.value_inr)).filter(
        Deal.org_id == org_id,
        Deal.stage.notin_([DealStage.CLOSED_LOST]),
    ).scalar() or 0

    deals_by_stage = {}
    for stage in DealStage:
        count = db.query(func.count(Deal.id)).filter(
            Deal.org_id == org_id, Deal.stage == stage
        ).scalar()
        deals_by_stage[stage.value] = count

    risk_flagged = db.query(func.count(Deal.id)).filter(
        Deal.org_id == org_id, Deal.risk_flag == True
    ).scalar()

    top_companies = (
        db.query(Company)
        .filter(Company.org_id == org_id)
        .order_by(Company.growth_signal.desc().nullslast())
        .limit(5)
        .all()
    )

    return {
        "total_pipeline_value": total_pipeline,
        "deals_by_stage": deals_by_stage,
        "risk_flagged_deals": risk_flagged,
        "forecast_gap_pct": None,
        "top_companies": top_companies,
    }


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get a specific deal (org-scoped)."""
    _, org_id, _ = user_org_role
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.org_id == org_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    deal: DealCreate,
    request: Request,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Create a new deal for the current org."""
    user, org_id, _ = user_org_role
    db_deal = Deal(**deal.model_dump(), org_id=org_id)
    db.add(db_deal)
    db.flush()
    write_audit_log(
        db, org_id, user.id, AuditAction.CREATE, "deal", db_deal.id, None,
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(db_deal)
    return db_deal


@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int,
    deal_update: DealUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Update a deal (org-scoped)."""
    user, org_id, _ = user_org_role
    db_deal = db.query(Deal).filter(Deal.id == deal_id, Deal.org_id == org_id).first()
    if not db_deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    updates = deal_update.model_dump(exclude_unset=True)
    before = {k: getattr(db_deal, k) for k in updates}

    for field, value in updates.items():
        setattr(db_deal, field, value)

    write_audit_log(
        db, org_id, user.id, AuditAction.UPDATE, "deal", deal_id,
        {"before": before, "after": updates},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(db_deal)
    return db_deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(require_role(OrgRole.ADMIN)),
):
    """Delete a deal — requires admin or owner role."""
    user, org_id, _ = user_org_role
    db_deal = db.query(Deal).filter(Deal.id == deal_id, Deal.org_id == org_id).first()
    if not db_deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    write_audit_log(
        db, org_id, user.id, AuditAction.DELETE, "deal", deal_id, None,
        request.client.host if request.client else None,
    )
    db.delete(db_deal)
    db.commit()
    return None
