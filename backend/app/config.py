"""
Application configuration via pydantic-settings.
All settings are loaded from environment variables.
In production (APP_ENV=production), insecure defaults cause startup failure.
"""
import secrets
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # ── Environment ───────────────────────────────────────────
    APP_ENV: str = "development"

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./lakshya.db"

    # ── JWT / Auth ────────────────────────────────────────────
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION_MIN_32_CHARS!!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15       # short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Email ─────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@lakshya.ai"
    FRONTEND_URL: str = "http://localhost:5173"
    REQUIRE_EMAIL_VERIFICATION: bool = False    # flip to True to enforce

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = ""                         # empty → in-memory fallback

    # ── File storage ──────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    # S3 / R2 (optional — local filesystem used when not set)
    AWS_S3_BUCKET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"

    # ── AI APIs ───────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── Google OAuth (stubbed) ────────────────────────────────
    GOOGLE_OAUTH_ENABLED: bool = False
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── CORS ──────────────────────────────────────────────────
    # Comma-separated list of extra allowed origins (e.g. Vercel preview URLs)
    ALLOWED_EXTRA_ORIGINS: str = ""

    # ── Rate limiting ─────────────────────────────────────────
    AUTH_RATE_LIMIT_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 900   # 15 min
    ORG_RATE_LIMIT_REQUESTS: int = 1000
    ORG_RATE_LIMIT_WINDOW_SECONDS: int = 3600   # 1 hour

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        # info.data may not have APP_ENV yet during validation order;
        # we check the insecure default explicitly.
        insecure = "CHANGE_ME_IN_PRODUCTION_MIN_32_CHARS!!"
        import os
        env = os.getenv("APP_ENV", "development")
        if env == "production":
            if v == insecure or len(v) < 32:
                raise ValueError(
                    "JWT_SECRET must be at least 32 characters and must not be the "
                    "default placeholder value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        """Railway uses postgres:// — SQLAlchemy needs postgresql://"""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @property
    def allowed_origins(self) -> list[str]:
        origins = [self.FRONTEND_URL.rstrip("/")]
        for o in self.ALLOWED_EXTRA_ORIGINS.split(","):
            o = o.strip()
            if o:
                origins.append(o)
        return origins

    @property
    def s3_enabled(self) -> bool:
        return bool(self.AWS_S3_BUCKET and self.AWS_ACCESS_KEY_ID)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
