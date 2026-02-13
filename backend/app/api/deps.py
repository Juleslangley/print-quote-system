from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("missing sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str):
    roles_set = set(roles)

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles_set:
            raise HTTPException(status_code=403, detail=f"Requires role(s): {', '.join(sorted(roles_set))}")
        return user

    return _guard


require_admin = require_roles("admin")
require_sales = require_roles("admin", "sales")
require_prod_or_better = require_roles("admin", "sales", "production")
require_packer = require_roles("admin", "packer")
