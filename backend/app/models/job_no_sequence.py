from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from app.core.db import Base


class JobNoSequence(Base):
    __tablename__ = "job_no_sequence"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    next_val: Mapped[int] = mapped_column(Integer, default=1)
