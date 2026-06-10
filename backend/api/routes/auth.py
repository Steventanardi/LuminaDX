"""Doctor authentication and admin user management."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from core.auth_utils import create_access_token, hash_password, verify_password, decode_token
from core.database import User, get_db

router = APIRouter()

VALID_ROLES = {"admin", "chief_physician", "radiologist"}


# ── Request / response models ──────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class CreateUserRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "radiologist"
    department: Optional[str] = None


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AdminResetPasswordRequest(BaseModel):
    new_password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * settings.auth_token_expire_hours,
        path="/",
    )


def _get_caller(access_token: Optional[str], db: Session) -> Optional[User]:
    if not access_token:
        return None
    payload = decode_token(access_token)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload.get("sub"), User.is_active == True).first()


def _require_admin_caller(access_token: Optional[str], db: Session) -> User:
    caller = _get_caller(access_token, db)
    if not caller:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if caller.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return caller


# ── Auth endpoints ─────────────────────────────────────────────────────────────

@router.post("/login", response_model=UserOut)
async def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email, User.is_active == True).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, user.role)
    _set_auth_cookie(response, token)

    user.last_login = datetime.utcnow()
    db.commit()
    return UserOut.model_validate(user)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(
    access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
):
    caller = _get_caller(access_token, db)
    if not caller:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserOut.model_validate(caller)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None),
):
    caller = _get_caller(access_token, db)
    if not caller:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not verify_password(req.current_password, caller.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    caller.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"message": "Password updated"}


# ── Admin user management ──────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None),
):
    _require_admin_caller(access_token, db)
    return [UserOut.model_validate(u) for u in db.query(User).order_by(User.created_at).all()]


@router.post("/users", response_model=UserOut)
async def create_user(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None),
):
    _require_admin_caller(access_token, db)

    if req.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    new_user = User(
        email=req.email,
        full_name=req.full_name,
        hashed_password=hash_password(req.password),
        role=req.role,
        department=req.department,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserOut.model_validate(new_user)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None),
):
    caller = _require_admin_caller(access_token, db)

    if caller.id == user_id and req.role is not None and req.role != "admin":
        raise HTTPException(status_code=400, detail="Admins cannot demote themselves")
    if caller.id == user_id and req.is_active is False:
        raise HTTPException(status_code=400, detail="Admins cannot deactivate themselves")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if req.full_name is not None:
        target.full_name = req.full_name
    if req.role is not None:
        if req.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")
        target.role = req.role
    if req.department is not None:
        target.department = req.department if req.department.strip() else None
    if req.is_active is not None:
        target.is_active = req.is_active

    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    req: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None),
):
    _require_admin_caller(access_token, db)
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    target.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"message": f"Password reset for {target.email}"}
