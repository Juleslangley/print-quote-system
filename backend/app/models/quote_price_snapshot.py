"""QuotePriceSnapshot: locked pricing revisions with input_hash for no-op lock prevention."""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.db import Base


class QuotePriceSnapshot(Base):
    __tablename__ = "quote_price_snapshots"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    quote_id: Mapped[str] = mapped_column(String, ForeignKey("quotes.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    pricing_version: Mapped[str] = mapped_column(String)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    result_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
