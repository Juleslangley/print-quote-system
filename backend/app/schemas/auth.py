from typing import List
from pydantic import BaseModel


class LoginIn(BaseModel):
    email: str  # allow e.g. admin@local for dev
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    active: bool
    menu_allow: List[str]
    menu_deny: List[str]
    visible_menu: List[str]
