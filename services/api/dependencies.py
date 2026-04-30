"""
services/api/dependencies.py
==============================
FastAPI dependency injection — shared auth guard.
Use `Depends(get_current_user)` in any route that requires authentication.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from services.api.config import get_settings
from services.api.logger import get_logger
from shared.db.base import SessionLocal
from shared.db.models import User

settings = get_settings()
logger   = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


# ── DB session ────────────────────────────────────────────────────────────────
def get_db():
    """Yield a SQLAlchemy session, closing it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Auth guard ────────────────────────────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode JWT and return the authenticated User.
    Raises 401 if token is missing, expired, or invalid.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exc

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError as e:
        logger.warning(f"[Auth] JWT decode failed: {e}")
        raise credentials_exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exc

    return user


async def get_optional_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of raising 401."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        return None
