from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db import get_db
from app.models import AuditAction, Company, User
from app.schemas import CompanyCreate, CompanyResponse
from app.routers.auth import (
    get_current_user_with_org,
    require_role,
    write_audit_log,
    OrgRole,
)

router = APIRouter()


@router.get("/", response_model=List[CompanyResponse])
def get_companies(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get companies for the current org with optional filters."""
    _, org_id, _ = user_org_role
    query = db.query(Company).filter(Company.org_id == org_id)

    if search:
        query = query.filter(Company.name.ilike(f"%{search}%"))
    if industry:
        query = query.filter(Company.industry == industry)
    if city:
        query = query.filter(Company.city == city)

    return query.offset(skip).limit(limit).all()


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get a specific company (org-scoped)."""
    _, org_id, _ = user_org_role
    company = db.query(Company).filter(
        Company.id == company_id, Company.org_id == org_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    company: CompanyCreate,
    request: Request,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Create a new company for the current org."""
    user, org_id, _ = user_org_role
    db_company = Company(**company.model_dump(), org_id=org_id)
    db.add(db_company)
    db.flush()
    write_audit_log(
        db, org_id, user.id, AuditAction.CREATE, "company", db_company.id, None,
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(db_company)
    return db_company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(require_role(OrgRole.ADMIN)),
):
    """Delete a company — requires admin or owner role."""
    user, org_id, _ = user_org_role
    db_company = db.query(Company).filter(
        Company.id == company_id, Company.org_id == org_id
    ).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    write_audit_log(
        db, org_id, user.id, AuditAction.DELETE, "company", company_id, None,
        request.client.host if request.client else None,
    )
    db.delete(db_company)
    db.commit()
    return None
