import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.base import new_id
from app.schemas.user import UserCreate, UserUpdate, UserOut, UserPasswordUpdate
from app.api.permissions import require_admin

router = APIRouter()
VALID_ROLES = frozenset({"admin", "sales", "production"})


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(User).order_by(User.email.asc()).all()


@router.post("/users", response_model=dict)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    if db.query(User).filter(User.email == payload.email.strip().lower()).first():
        raise HTTPException(status_code=400, detail="Email already in use")
    role = (payload.role or "sales").strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="role must be one of: admin, sales, production")
    password = payload.password
    if not password or not password.strip():
        password = secrets.token_urlsafe(12)
        temp_password = password
    else:
        temp_password = None
    u = User(
        id=new_id(),
        email=payload.email.strip().lower(),
        password_hash=hash_password(password),
        full_name=(payload.full_name or "").strip(),
        role=role,
        active=payload.active,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    out = UserOut.model_validate(u)
    result = {"user": out.model_dump()}
    if temp_password:
        result["temp_password"] = temp_password
    return result


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] is not None:
        r = data["role"].strip().lower()
        if r not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="role must be one of: admin, sales, production")
        data["role"] = r
    for k, v in data.items():
        setattr(u, k, v)
    db.add(u)
    db.commit()
    db.refresh(u)
    return UserOut.model_validate(u)


@router.put("/users/{user_id}/password")
def update_user_password(
    user_id: str,
    payload: UserPasswordUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.password_hash = hash_password(payload.new_password)
    db.add(u)
    db.commit()
    return {"ok": True}
