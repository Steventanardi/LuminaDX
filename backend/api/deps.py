from typing import Optional

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth_utils import decode_token
from core.database import User, get_db


# ── Authentication ────────────────────────────────────────────────────────────

async def get_current_user(
    access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ── Role-based resource access ────────────────────────────────────────────────

def can_view(owner_user_id: Optional[str], owner_department: Optional[str], user: User) -> bool:
    """Return True if *user* may read a resource owned by *owner_user_id*."""
    if user.role == "admin":
        return True
    if owner_user_id and owner_user_id == user.id:
        return True
    if (
        user.role == "chief_physician"
        and owner_department
        and user.department
        and owner_department == user.department
    ):
        return True
    return False


def can_modify(owner_user_id: Optional[str], user: User) -> bool:
    """Return True if *user* may write/delete a resource owned by *owner_user_id*."""
    if user.role == "admin":
        return True
    if owner_user_id and owner_user_id == user.id:
        return True
    return False


def assert_view(owner_user_id: Optional[str], owner_department: Optional[str], user: User) -> None:
    """Raise 404 (not 403 — don't leak existence) if user cannot read the resource."""
    if not can_view(owner_user_id, owner_department, user):
        raise HTTPException(status_code=404, detail="Not found")


def assert_modify(owner_user_id: Optional[str], user: User) -> None:
    """Raise 403 if user cannot modify the resource."""
    if not can_modify(owner_user_id, user):
        raise HTTPException(status_code=403, detail="You do not have permission to modify this resource")
