from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import engine, Base
from app.routers import auth, deals, companies, whatsapp_intelligence, call_intelligence, forecasting
import os

# Create database tables
Base.metadata.create_all(bind=engine)

# Auto-seed demo data on first startup (runs in production too)
def _auto_seed():
    try:
        from app.db import SessionLocal
        from app.models import User
        db = SessionLocal()
        if db.query(User).count() == 0:
            db.close()
            import sys, importlib.util, pathlib
            seed_path = pathlib.Path(__file__).parent.parent / "seed_data.py"
            if seed_path.exists():
                spec = importlib.util.spec_from_file_location("seed_data", seed_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.seed_data()
        else:
            db.close()
    except Exception as e:
        print(f"Auto-seed skipped: {e}")

_auto_seed()

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

app = FastAPI(
    title="LAKSHYA AI API",
    description="B2B Revenue Intelligence Platform for Indian Market",
    version="1.0.0"
)

# CORS middleware — allow local dev + any Vercel/Railway deployment
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
]
# Add FRONTEND_URL from env (set on Railway/Vercel) if present
_frontend_url = os.getenv("FRONTEND_URL", "")
if _frontend_url:
    ALLOWED_ORIGINS.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",  # all Vercel preview URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(deals.router, prefix="/api/deals", tags=["Deals"])
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
app.include_router(whatsapp_intelligence.router, prefix="/api/whatsapp", tags=["WhatsApp Intelligence"])
app.include_router(call_intelligence.router, prefix="/api/calls", tags=["Call Intelligence"])
app.include_router(forecasting.router, prefix="/api/forecast", tags=["Forecasting"])


@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "LAKSHYA AI API", "status": "running"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/status")
def api_status():
    """Reports which optional integrations are configured (no secrets exposed)"""
    return {
        "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }
