"""
Auth router — Phase 6 hardened implementation.

Changes from MVP:
- bcrypt password hashing (replaces SHA-256)
- SHA-256 → bcrypt migration on next login
- Short-lived access tokens (15 min) + revocable refresh tokens (7 days)
- Email verification flow
- Password reset flow
- Rate limiting on login/register (5 attempts / 15 min / IP)
- Google OAuth stub behind GOOGLE_OAUTH_ENABLED feature flag
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AuditAction, OrgMember, OrgRole, Organization, RefreshToken, User
from app.schemas import (
    OrgCreate,
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.email import send_verification_email, send_password_reset_email
from app.services.rate_limiter import check_rate_limit

settings = get_settings()

router = APIRouter()

# ─────────────────────────────────────────────────────────────
# Password hashing
# ─────────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def _sha256_hash(password: str) -> str:
    """Legacy SHA-256 hash used in MVP. Only used for migration check."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password against a stored hash.
    Handles both bcrypt hashes (current) and legacy SHA-256 hashes (MVP).
    """
    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        return pwd_context.verify(plain, hashed)
    # Legacy SHA-256 path — still accepted during migration window
    return _sha256_hash(plain) == hashed


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _maybe_upgrade_hash(user: User, plain_password: str, db: Session) -> None:
    """
    If the user still has a SHA-256 hash, transparently re-hash with bcrypt
    on successful login. This silently migrates the account.
    """
    if user.password_hash and not (
        user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
    ):
        user.password_hash = hash_password(plain_password)
        db.commit()


# ─────────────────────────────────────────────────────────────
# JWT helpers
# ─────────────────────────────────────────────────────────────

def create_access_token(
    user_id: int,
    org_id: int,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _hash_token(token: str) -> str:
    """SHA-256 hash of an opaque token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(user_id: int, db: Session) -> str:
    """
    Generate a 32-byte opaque refresh token, store its hash in DB, return raw token.
    """
    raw = secrets.token_hex(32)
    token_hash = _hash_token(raw)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()
    return raw


# ─────────────────────────────────────────────────────────────
# Current-user dependency
# ─────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: decode JWT, return User. Raises 401 on any failure."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise exc
    except JWTError:
        raise exc

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise exc
    return user


def get_current_user_with_org(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> tuple[User, int, str]:
    """
    Returns (user, org_id, role) from the JWT.
    Raises 401 if token invalid, 403 if user has no org membership.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        org_id: int = payload.get("org_id")
        role: str = payload.get("role")
        if user_id is None or org_id is None:
            raise exc
    except JWTError:
        raise exc

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise exc
    return user, int(org_id), role


# ─────────────────────────────────────────────────────────────
# RBAC helper
# ─────────────────────────────────────────────────────────────

ROLE_RANK = {OrgRole.MEMBER: 0, OrgRole.ADMIN: 1, OrgRole.OWNER: 2}


def require_role(minimum_role: OrgRole):
    """
    FastAPI dependency factory.
    Usage: Depends(require_role(OrgRole.ADMIN))
    """
    def _check(
        user_org_role: tuple = Depends(get_current_user_with_org),
    ):
        _, _, role_str = user_org_role
        try:
            current = OrgRole(role_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid role in token")
        if ROLE_RANK.get(current, -1) < ROLE_RANK[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{minimum_role.value}' or higher",
            )
        return user_org_role

    return _check


# ─────────────────────────────────────────────────────────────
# Audit log helper (imported by other routers too)
# ─────────────────────────────────────────────────────────────

def write_audit_log(
    db: Session,
    org_id: int,
    user_id: int,
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[int],
    diff: Optional[dict],
    ip_address: Optional[str],
) -> None:
    from app.models import AuditLog
    entry = AuditLog(
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        diff_json=diff,
        ip_address=ip_address,
    )
    db.add(entry)
    # Caller is responsible for db.commit()


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Register a new user and create their organization.
    The registering user is automatically assigned the 'owner' role.
    """
    ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"register:{ip}", settings.AUTH_RATE_LIMIT_ATTEMPTS, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)

    # Check for duplicate email
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    verification_token = secrets.token_urlsafe(32)
    db_user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        is_email_verified=False,
        email_verification_token=verification_token,
    )
    db.add(db_user)
    db.flush()  # get db_user.id before commit

    # Create organization
    org = Organization(name=payload.org_name)
    db.add(org)
    db.flush()

    # Link user as owner
    membership = OrgMember(org_id=org.id, user_id=db_user.id, role=OrgRole.OWNER)
    db.add(membership)
    db.commit()
    db.refresh(db_user)

    # Send verification email (best-effort — don't fail registration if email fails)
    try:
        await send_verification_email(db_user.email, db_user.name, verification_token)
    except Exception:
        pass

    return db_user


@router.post("/login", response_model=Token)
async def login(
    payload: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    """Login: returns short-lived access token + long-lived refresh token."""
    ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"login:{ip}", settings.AUTH_RATE_LIMIT_ATTEMPTS, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)

    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Transparently upgrade legacy SHA-256 hash → bcrypt
    _maybe_upgrade_hash(user, payload.password, db)

    # Get org membership
    membership = db.query(OrgMember).filter(OrgMember.user_id == user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User has no organization. Contact support.")

    access_token = create_access_token(
        user_id=user.id,
        org_id=membership.org_id,
        role=membership.role.value,
    )
    refresh_token = create_refresh_token(user_id=user.id, db=db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_email_verified": user.is_email_verified,
    }


@router.post("/refresh", response_model=Token)
def refresh_token_endpoint(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token + rotated refresh token.
    The old refresh token is revoked.
    """
    raw_token = payload.get("refresh_token")
    if not raw_token:
        raise HTTPException(status_code=400, detail="refresh_token required")

    token_hash = _hash_token(raw_token)
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
    ).first()

    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalid or expired",
        )

    # Revoke old token (rotation)
    db_token.revoked = True
    db.commit()

    user = db.query(User).filter(User.id == db_token.user_id).first()
    membership = db.query(OrgMember).filter(OrgMember.user_id == user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User has no organization")

    access_token = create_access_token(
        user_id=user.id,
        org_id=membership.org_id,
        role=membership.role.value,
    )
    new_refresh = create_refresh_token(user_id=user.id, db=db)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "is_email_verified": user.is_email_verified,
    }


@router.post("/logout")
def logout(
    payload: dict,
    db: Session = Depends(get_db),
):
    """Revoke the presented refresh token."""
    raw_token = payload.get("refresh_token")
    if not raw_token:
        raise HTTPException(status_code=400, detail="refresh_token required")

    token_hash = _hash_token(raw_token)
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()
    if db_token:
        db_token.revoked = True
        db.commit()

    return {"message": "Logged out successfully"}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify user email via token sent during registration."""
    user = db.query(User).filter(User.email_verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user.is_email_verified = True
    user.email_verification_token = None
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(payload: dict, db: Session = Depends(get_db)):
    """
    Send a password reset email.
    Always returns the same response to prevent email enumeration.
    """
    email = payload.get("email", "")
    user = db.query(User).filter(User.email == email).first()

    if user and user.provider is None:  # Can't reset OAuth-only accounts
        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = _hash_token(reset_token)
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        try:
            await send_password_reset_email(user.email, user.name, reset_token)
        except Exception:
            pass  # Don't reveal email/SMTP errors to the caller

    return {"message": "If that email is registered, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(payload: dict, db: Session = Depends(get_db)):
    """Reset password using a valid reset token."""
    token = payload.get("token", "")
    new_password = payload.get("new_password", "")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="token and new_password required")

    if len(new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    token_hash = _hash_token(token)
    user = db.query(User).filter(
        User.password_reset_token == token_hash,
        User.password_reset_expires > datetime.utcnow(),
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = hash_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()

    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return current_user


# ─────────────────────────────────────────────────────────────
# Google OAuth stub
# ─────────────────────────────────────────────────────────────

@router.get("/google")
def google_oauth_start():
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Google OAuth is not enabled")
    # TODO Phase 6.4: implement redirect to Google consent screen
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/google/callback")
def google_oauth_callback():
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Google OAuth is not enabled")
    # TODO Phase 6.4: exchange code, create/find user, issue tokens
    raise HTTPException(status_code=501, detail="Not implemented yet")
