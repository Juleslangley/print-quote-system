from typing import Optional, List
from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    email: str
    full_name: str = ""
    role: str = "sales"  # admin, sales, production
    password: Optional[str] = None  # if blank, backend generates temp
    active: bool = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    menu_allow: Optional[List[str]] = None
    menu_deny: Optional[List[str]] = None


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = ""
    role: str
    active: bool
    menu_allow: List[str] = []
    menu_deny: List[str] = []

    class Config:
        from_attributes = True

    @field_validator("menu_allow", "menu_deny", mode="before")
    @classmethod
    def empty_list_if_none(cls, v):
        return v if v is not None else []


class UserPasswordUpdate(BaseModel):
    new_password: str
