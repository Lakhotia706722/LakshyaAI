"""
Lakshya AI — FastAPI application entry point.
Phase 6: multi-tenancy, hardened auth, security headers, per-org rate limiting.
"""
from __future__ import annotations

import os
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, deals, companies, whatsapp_intelligence, call_intelligence, forecasting
from app.routers import org as org_router

settings = get_settings()

# ─────────────────────────────────────────────────────────────
# Schema creation (dev only) + auto-seed
# ─────────────────────────────────────────────────────────────

def _create_tables():
    """
    Create DB tables via SQLAlchemy metadata.
    Only runs in development — in production, Alembic handles migrations.
    """
    if settings.APP_ENV != "production":
        from app.db import engine, Base
        import app.models  # noqa: F401 — ensure all models are registered
        Base.metadata.create_all(bind=engine)


def _auto_seed():
    """Seed demo data on first startup if the DB is empty (dev only)."""
    if settings.APP_ENV == "production":
        return
    try:
        from app.db import SessionLocal
        from app.models import User
        db = SessionLocal()
        if db.query(User).count() == 0:
            db.close()
            import importlib.util
            import pathlib
            seed_path = pathlib.Path(__file__).parent.parent / "seed_data.py"
            if seed_path.exists():
                spec = importlib.util.spec_from_file_location("seed_data", seed_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "seed_data"):
                    mod.seed_data()
        else:
            db.close()
    except Exception as e:
        print(f"Auto-seed skipped: {e}")


_create_tables()
_auto_seed()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="LAKSHYA AI API",
    description="B2B Revenue Intelligence Platform for Indian Market",
    version="2.0.0",
)

# ─────────────────────────────────────────────────────────────
# CORS — locked to explicit origins only
# ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ─────────────────────────────────────────────────────────────
# Security headers middleware
# ─────────────────────────────────────────────────────────────

@app.middleware("http")
async def add_security_headers(request: Request, call_next: Callable) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# ─────────────────────────────────────────────────────────────
# Per-org API rate limiting middleware
# ─────────────────────────────────────────────────────────────

@app.middleware("http")
async def per_org_rate_limit(request: Request, call_next: Callable) -> Response:
    """
    Apply a per-org request rate limit on non-auth API routes.
    Extracts org_id from the JWT without full validation (fast path).
    """
    path = request.url.path
    # Skip rate limiting for auth endpoints and non-API routes
    if not path.startswith("/api/") or path.startswith("/api/auth"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from jose import jwt as _jwt
            payload = _jwt.decode(
                token, settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False},  # exp already checked in route
            )
            org_id = payload.get("org_id")
            if org_id:
                from app.services.rate_limiter import check_rate_limit
                await check_rate_limit(
                    f"org_api:{org_id}",
                    settings.ORG_RATE_LIMIT_REQUESTS,
                    settings.ORG_RATE_LIMIT_WINDOW_SECONDS,
                )
        except Exception:
            pass  # Let the route's auth dependency handle invalid tokens

    return await call_next(request)


# ─────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(deals.router, prefix="/api/deals", tags=["Deals"])
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
app.include_router(whatsapp_intelligence.router, prefix="/api/whatsapp", tags=["WhatsApp Intelligence"])
app.include_router(call_intelligence.router, prefix="/api/calls", tags=["Call Intelligence"])
app.include_router(forecasting.router, prefix="/api/forecast", tags=["Forecasting"])
app.include_router(org_router.router, prefix="/api/org", tags=["Organization"])


# ─────────────────────────────────────────────────────────────
# Utility endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "LAKSHYA AI API", "status": "running", "version": "2.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/api/status")
def api_status():
    """Reports which optional integrations are configured (no secrets exposed)."""
    return {
        "anthropic_configured": bool(settings.ANTHROPIC_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "s3_configured": settings.s3_enabled,
        "redis_configured": bool(settings.REDIS_URL),
    }
