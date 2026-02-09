from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String
from app.core.db import Base


class POSequence(Base):
    __tablename__ = "purchase_orders_sequence"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    next_val: Mapped[int] = mapped_column(Integer, default=1)
