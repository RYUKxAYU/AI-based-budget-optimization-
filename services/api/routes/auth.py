"""
services/api/routes/auth.py
============================
STEP 2 — Auth endpoints: POST /register | POST /login | GET /me
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from services.api.config import get_settings
from services.api.dependencies import get_db, get_current_user
from services.api.logger import get_logger
from shared.db.models import User

settings = get_settings()
logger   = get_logger(__name__)
router   = APIRouter(tags=["Auth"])

pwd_ctx  = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Schemas ───────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {"email": "user@example.com", "password": "securepass123"}
        }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserResponse(BaseModel):
    user_id: str
    email: str
    created_at: datetime
    is_active: bool = True


# ── Helpers ───────────────────────────────────────────────────────────────────
def _hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def _create_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=3600)
    payload = {
        "sub":   user.id,
        "email": user.email,
        "exp":   expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ── POST /register ────────────────────────────────────────────────────────────
@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new account.
    - Validates email format (RFC)
    - Password must be ≥ 8 characters
    - Returns `user_id` on success
    """
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        password_hash=_hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"[Auth] New user registered: {user.email}")
    return {"message": "Account created successfully.", "user_id": user.id}


# ── POST /login ───────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse, summary="Login and get JWT token")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate and receive a Bearer JWT token.
    Token expires in 3600 seconds (1 hour).
    """
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not _verify_password(req.password, user.password_hash):
        logger.warning(f"[Auth] Failed login attempt for: {req.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = _create_token(user)
    logger.info(f"[Auth] User logged in: {user.email}")
    return TokenResponse(access_token=token)


# ── GET /me ───────────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user's profile.
    Requires `Authorization: Bearer <token>` header.
    """
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
    )
