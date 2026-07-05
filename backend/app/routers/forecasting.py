"""
Phase 4 — Revenue Forecasting (Tally CSV reconciliation)
Now org-scoped — all data filtered by the current user's org.
"""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime

from app.db import get_db
from app.models import Company, Deal, Invoice, DealStage, ForecastSnapshot
from app.routers.auth import get_current_user_with_org

router = APIRouter()


def _fuzzy_match(name: str, companies: List[Company]) -> Company | None:
    name_lower = name.lower().strip()
    for c in companies:
        if c.name.lower() in name_lower or name_lower in c.name.lower():
            return c
    return None


@router.post("/upload-csv")
async def upload_tally_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Upload a Tally invoice export CSV and reconcile against CRM deals."""
    _, org_id, _ = user_org_role

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    content = await file.read()
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        rows = list(reader)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {str(e)}")

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    required_cols = {"company_name", "invoice_date", "amount", "status"}
    if not required_cols.issubset(set(rows[0].keys())):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must have columns: {', '.join(required_cols)}",
        )

    companies = db.query(Company).filter(Company.org_id == org_id).all()
    invoiced_total = 0
    matched_invoices = []
    unmatched_rows = []

    for row in rows:
        company = _fuzzy_match(row["company_name"], companies)
        amount = int(float(str(row["amount"]).replace(",", "").strip() or 0))

        try:
            inv_date = datetime.strptime(row["invoice_date"].strip(), "%Y-%m-%d").date()
        except ValueError:
            try:
                inv_date = datetime.strptime(row["invoice_date"].strip(), "%d/%m/%Y").date()
            except ValueError:
                inv_date = date.today()

        if company:
            invoice = Invoice(
                org_id=org_id,
                company_id=company.id,
                amount_inr=amount,
                invoice_date=inv_date,
                status=row["status"].strip().lower(),
            )
            db.add(invoice)
            invoiced_total += amount
            matched_invoices.append({
                "company_name": row["company_name"],
                "matched_to": company.name,
                "amount_inr": amount,
                "status": row["status"],
            })
        else:
            unmatched_rows.append(row["company_name"])

    db.commit()

    pipeline_value = sum(
        d.value_inr or 0
        for d in db.query(Deal).filter(
            Deal.org_id == org_id, Deal.stage != DealStage.CLOSED_LOST
        ).all()
    )

    closed_won_deals = db.query(Deal).filter(
        Deal.org_id == org_id, Deal.stage == DealStage.CLOSED_WON
    ).all()
    invoiced_company_ids = {
        i.company_id
        for i in db.query(Invoice).filter(Invoice.org_id == org_id).all()
    }
    unmatched_closed = [
        {
            "deal_id": d.id,
            "title": d.title,
            "company": d.company.name if d.company else "Unknown",
            "value_inr": d.value_inr,
        }
        for d in closed_won_deals
        if d.company_id not in invoiced_company_ids
    ]

    gap_pct = int(
        ((pipeline_value - invoiced_total) / pipeline_value * 100)
        if pipeline_value > 0 else 0
    )

    snapshot = ForecastSnapshot(
        org_id=org_id,
        pipeline_value_inr=pipeline_value,
        invoiced_value_inr=invoiced_total,
        gap_pct=gap_pct,
        notes=f"Imported {len(matched_invoices)} invoices from {file.filename}",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {
        "snapshot_id": snapshot.id,
        "pipeline_value_inr": pipeline_value,
        "invoiced_value_inr": invoiced_total,
        "gap_pct": gap_pct,
        "matched_invoices": len(matched_invoices),
        "unmatched_rows": unmatched_rows,
        "closed_won_not_invoiced": unmatched_closed,
    }


@router.get("/snapshot/latest")
def get_latest_snapshot(
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get the most recent forecast snapshot for the current org."""
    _, org_id, _ = user_org_role

    snap = (
        db.query(ForecastSnapshot)
        .filter(ForecastSnapshot.org_id == org_id)
        .order_by(ForecastSnapshot.generated_at.desc())
        .first()
    )

    if not snap:
        pipeline_value = sum(
            d.value_inr or 0
            for d in db.query(Deal).filter(
                Deal.org_id == org_id, Deal.stage != DealStage.CLOSED_LOST
            ).all()
        )
        return {
            "pipeline_value_inr": pipeline_value,
            "invoiced_value_inr": 0,
            "gap_pct": 100 if pipeline_value > 0 else 0,
            "notes": "No invoice data uploaded yet",
            "closed_won_not_invoiced": [],
        }

    closed_won = db.query(Deal).filter(
        Deal.org_id == org_id, Deal.stage == DealStage.CLOSED_WON
    ).all()
    invoiced_ids = {
        i.company_id
        for i in db.query(Invoice).filter(Invoice.org_id == org_id).all()
    }
    unmatched_closed = [
        {
            "deal_id": d.id,
            "title": d.title,
            "company": d.company.name if d.company else "Unknown",
            "value_inr": d.value_inr,
        }
        for d in closed_won if d.company_id not in invoiced_ids
    ]

    return {
        "pipeline_value_inr": snap.pipeline_value_inr,
        "invoiced_value_inr": snap.invoiced_value_inr,
        "gap_pct": snap.gap_pct,
        "notes": snap.notes,
        "generated_at": snap.generated_at,
        "closed_won_not_invoiced": unmatched_closed,
    }


@router.get("/sample-csv-template")
def get_sample_csv():
    """Return a sample CSV template for download."""
    csv_content = (
        "company_name,invoice_date,amount,status\n"
        "TechVision Solutions,2024-01-15,500000,paid\n"
        "Mehta Manufacturing Ltd,2024-01-20,1200000,pending\n"
        "Digital Finance Corp,2024-02-01,750000,paid\n"
        "CloudMinds Technologies,2024-02-10,300000,overdue\n"
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tally_invoice_template.csv"},
    )
