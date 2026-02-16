from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginIn, TokenOut, MeOut
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

# Menu keys used for Nav and Admin landing. visible_menu = (role_defaults ∪ menu_allow) − menu_deny
MENU_DEFAULTS_BY_ROLE = {
    "admin": [
        "home", "quotes", "admin", "materials", "customers",
        "admin.materials", "admin.suppliers", "admin.machines", "admin.customers", "admin.users",
        "admin.rates", "admin.operations", "admin.templates", "admin.margins", "admin.purchase_orders",
        "admin.documents",
        "admin.packing",
        "production", "packing",
    ],
    "sales": ["home", "quotes", "admin", "materials", "customers", "admin.customers", "admin.suppliers", "admin.purchase_orders", "admin.documents", "production"],
    "production": ["home", "production"],
    "packer": ["home", "packing"],
}


def _visible_menu(user: User) -> list[str]:
    role_defaults = list(MENU_DEFAULTS_BY_ROLE.get(user.role, MENU_DEFAULTS_BY_ROLE["production"]))
    allow = list(user.menu_allow) if getattr(user, "menu_allow", None) else []
    deny = set(user.menu_deny) if getattr(user, "menu_deny", None) else set()
    combined = set(role_defaults) | set(allow)
    return sorted(combined - deny)


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id)
    return TokenOut(access_token=token)


@router.get("/auth/me", response_model=MeOut)
def auth_me(user: User = Depends(get_current_user)):
    return _me_response(user)


def _me_response(user: User) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name or "",
        role=user.role,
        active=user.active,
        menu_allow=list(getattr(user, "menu_allow", None) or []),
        menu_deny=list(getattr(user, "menu_deny", None) or []),
        visible_menu=_visible_menu(user),
    )


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    """Current user. Alias for /auth/me for backward compatibility."""
    return _me_response(user)
