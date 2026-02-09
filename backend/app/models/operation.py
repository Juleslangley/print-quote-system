from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON
from app.core.db import Base
from app.models.base import TimestampMixin

class Operation(Base, TimestampMixin):
    """
    This is your reusable admin "operation library".
    Example operations:
      CUT_STRAIGHT, CUT_CONTOUR, ROUTER_CUT, LAMINATE_ROLL, HEM_AND_EYELET, PACK_STANDARD
    """
    __tablename__ = "operations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)  # e.g. "CUT_STRAIGHT"
    name: Mapped[str] = mapped_column(String, index=True)              # friendly label
    rate_type: Mapped[str] = mapped_column(String, index=True)         # cut_knife/cut_router/laminate/pack etc.

    # calc_model determines how we compute run time and consumables
    # Supported v1 models:
    #   PERIM_M, SQM, ITEM, ROUTER_PERIM_M, LAM_SQM
    calc_model: Mapped[str] = mapped_column(String, index=True)

    # default parameters for this operation
    params: Mapped[dict] = mapped_column(JSON, default=dict)

    active: Mapped[bool] = mapped_column(Boolean, default=True)
