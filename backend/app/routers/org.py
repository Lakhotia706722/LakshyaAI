"""
Org management router.

Provides:
- GET  /api/org                — get current org info
- GET  /api/org/members        — list org members
- GET  /api/audit-log          — paginated audit log (admin+)
- GET  /api/org/export         — full data export JSON (owner only)
- DELETE /api/org              — delete entire org (owner only, requires confirmation)
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AuditAction,
    AuditLog,
    CallRecording,
    Company,
    ConsentRecord,
    Deal,
    DealEvent,
    ForecastSnapshot,
    Invoice,
    OrgMember,
    OrgRole,
    Organization,
    RefreshToken,
    User,
)
from app.routers.auth import (
    get_current_user_with_org,
    require_role,
    write_audit_log,
)
from app.schemas import AuditLogResponse, OrgMemberResponse, OrgResponse
from app.services.file_storage import delete_audio_file

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Org info
# ─────────────────────────────────────────────────────────────

@router.get("", response_model=OrgResponse)
def get_org(
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Return the current user's organization."""
    _, org_id, _ = user_org_role
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/members", response_model=List[OrgMemberResponse])
def get_members(
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """List all members of the current org."""
    _, org_id, _ = user_org_role
    return db.query(OrgMember).filter(OrgMember.org_id == org_id).all()


# ─────────────────────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────────────────────

@router.get("/audit-log", response_model=List[AuditLogResponse])
def get_audit_log(
    resource_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(require_role(OrgRole.ADMIN)),
):
    """Paginated audit log — admin and owner only."""
    _, org_id, _ = user_org_role
    query = db.query(AuditLog).filter(AuditLog.org_id == org_id)

    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if from_date:
        query = query.filter(AuditLog.timestamp >= from_date)
    if to_date:
        query = query.filter(AuditLog.timestamp <= to_date)

    return (
        query.order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


# ─────────────────────────────────────────────────────────────
# Data export
# ─────────────────────────────────────────────────────────────

@router.get("/export")
def export_org_data(
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(require_role(OrgRole.OWNER)),
):
    """
    Export all org data as a JSON file download.
    Owner only. Raw audio files are NOT included — only metadata.
    """
    _, org_id, _ = user_org_role

    org = db.query(Organization).filter(Organization.id == org_id).first()
    members = db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    companies = db.query(Company).filter(Company.org_id == org_id).all()
    deals = db.query(Deal).filter(Deal.org_id == org_id).all()
    deal_events = db.query(DealEvent).filter(DealEvent.org_id == org_id).all()
    recordings = db.query(CallRecording).filter(CallRecording.org_id == org_id).all()
    invoices = db.query(Invoice).filter(Invoice.org_id == org_id).all()
    snapshots = db.query(ForecastSnapshot).filter(ForecastSnapshot.org_id == org_id).all()
    consents = db.query(ConsentRecord).filter(ConsentRecord.org_id == org_id).all()

    def _dt(v):
        return v.isoformat() if isinstance(v, datetime) else str(v) if v else None

    export = {
        "exported_at": datetime.utcnow().isoformat(),
        "organization": {
            "id": org.id, "name": org.name,
            "plan_tier": org.plan_tier,
            "created_at": _dt(org.created_at),
        },
        "members": [
            {"user_id": m.user_id, "role": m.role.value, "created_at": _dt(m.created_at)}
            for m in members
        ],
        "companies": [
            {
                "id": c.id, "name": c.name, "industry": c.industry,
                "city": c.city, "state": c.state, "gst_number": c.gst_number,
                "created_at": _dt(c.created_at),
            }
            for c in companies
        ],
        "deals": [
            {
                "id": d.id, "title": d.title, "stage": d.stage.value,
                "value_inr": d.value_inr, "company_id": d.company_id,
                "risk_flag": d.risk_flag, "created_at": _dt(d.created_at),
            }
            for d in deals
        ],
        "deal_events": [
            {
                "id": e.id, "deal_id": e.deal_id, "source": e.source.value,
                "extracted_summary": e.extracted_summary,
                "next_step": e.next_step,
                "created_at": _dt(e.created_at),
                # raw_text intentionally omitted — may contain PII
            }
            for e in deal_events
        ],
        "call_recordings": [
            {
                "id": r.id, "deal_id": r.deal_id, "language": r.language,
                "transcript": r.transcript,
                "analysis_json": r.analysis_json,
                "created_at": _dt(r.created_at),
                # file_path intentionally omitted
            }
            for r in recordings
        ],
        "invoices": [
            {
                "id": i.id, "company_id": i.company_id, "deal_id": i.deal_id,
                "amount_inr": i.amount_inr, "invoice_date": _dt(i.invoice_date),
                "status": i.status, "created_at": _dt(i.created_at),
            }
            for i in invoices
        ],
        "forecast_snapshots": [
            {
                "id": s.id, "pipeline_value_inr": s.pipeline_value_inr,
                "invoiced_value_inr": s.invoiced_value_inr,
                "gap_pct": s.gap_pct, "generated_at": _dt(s.generated_at),
            }
            for s in snapshots
        ],
        "consent_records": [
            {
                "id": c.id, "data_subject_identifier": c.data_subject_identifier,
                "consent_type": c.consent_type.value, "consent_source": c.consent_source,
                "consented_at": _dt(c.consented_at), "withdrawn_at": _dt(c.withdrawn_at),
            }
            for c in consents
        ],
    }

    content = json.dumps(export, indent=2, ensure_ascii=False)
    filename = f"lakshya_export_{org.name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.json"
    return JSONResponse(
        content=export,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────────────────────
# Data deletion (DPDP compliance)
# ─────────────────────────────────────────────────────────────

@router.delete("")
def delete_org(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(require_role(OrgRole.OWNER)),
):
    """
    Permanently delete the entire organization and all its data.
    Owner only. Requires confirmation body: {"confirm": "DELETE <org_name>"}
    """
    user, org_id, _ = user_org_role

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    expected = f"DELETE {org.name}"
    if payload.get("confirm") != expected:
        raise HTTPException(
            status_code=400,
            detail=f'Confirmation required. Send {{"confirm": "{expected}"}}',
        )

    # Write audit entry BEFORE deletion (special case — org won't exist after)
    write_audit_log(
        db, org_id, user.id, AuditAction.DELETE, "organization", org_id,
        {"org_name": org.name, "reason": "owner_requested_deletion"},
        request.client.host if request.client else None,
    )
    db.commit()

    # Delete audio files from disk/S3 first
    recordings = db.query(CallRecording).filter(CallRecording.org_id == org_id).all()
    for rec in recordings:
        delete_audio_file(rec.file_path, rec.storage_type)

    # Delete all data tables in dependency order
    db.query(ConsentRecord).filter(ConsentRecord.org_id == org_id).delete()
    db.query(AuditLog).filter(AuditLog.org_id == org_id).delete()
    db.query(ForecastSnapshot).filter(ForecastSnapshot.org_id == org_id).delete()
    db.query(Invoice).filter(Invoice.org_id == org_id).delete()
    db.query(CallRecording).filter(CallRecording.org_id == org_id).delete()
    db.query(DealEvent).filter(DealEvent.org_id == org_id).delete()
    db.query(Deal).filter(Deal.org_id == org_id).delete()
    db.query(Company).filter(Company.org_id == org_id).delete()

    # Revoke all refresh tokens for org members
    member_user_ids = [
        m.user_id
        for m in db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    ]
    for uid in member_user_ids:
        db.query(RefreshToken).filter(RefreshToken.user_id == uid).delete()

    db.query(OrgMember).filter(OrgMember.org_id == org_id).delete()
    db.query(Organization).filter(Organization.id == org_id).delete()
    db.commit()

    return {"message": f"Organization '{org.name}' and all associated data have been permanently deleted."}
