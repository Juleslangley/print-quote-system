from typing import Optional
from pydantic import BaseModel

class OperationCreate(BaseModel):
    code: str
    name: str
    rate_type: str
    calc_model: str
    params: dict = {}
    active: bool = True

class OperationUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    rate_type: Optional[str] = None
    calc_model: Optional[str] = None
    params: Optional[dict] = None
    active: Optional[bool] = None

class OperationOut(BaseModel):
    id: str
    code: str
    name: str
    rate_type: str
    calc_model: str
    params: dict
    active: bool

    class Config:
        from_attributes = True
