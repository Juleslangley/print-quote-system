from pydantic import BaseModel


class JobOpOut(BaseModel):
    sort_order: int
    code: str
    name: str
    calc_model: str
    rate_type: str
    params: dict


class JobItemOut(BaseModel):
    item_id: str
    title: str
    template_id: str
    template_name: str
    category: str

    qty: int
    width_mm: float
    height_mm: float
    sides: int
    options: dict

    material_id: str
    material_name: str

    operations: list[JobOpOut]


class JobTicketOut(BaseModel):
    quote_id: str
    quote_number: str
    customer_id: str
    customer_name: str
    status: str
    notes_internal: str

    items: list[JobItemOut]
