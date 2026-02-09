from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, JSON
from app.core.db import Base
from app.models.base import TimestampMixin, new_id

class TemplateOperation(Base, TimestampMixin):
    """Links a product template to an operation (e.g. which operations apply to this template, and in what order)."""
    __tablename__ = "template_operations"
    __table_args__ = (UniqueConstraint("template_id", "operation_id", name="uq_template_operation"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("product_templates.id"), index=True)
    operation_id: Mapped[str] = mapped_column(String, ForeignKey("operations.id"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    params_override: Mapped[dict] = mapped_column(JSON, default=dict)


class TemplateAllowedMaterial(Base, TimestampMixin):
    """Links a product template to allowed materials (which materials can be used with this template)."""
    __tablename__ = "template_allowed_materials"
    __table_args__ = (UniqueConstraint("template_id", "material_id", name="uq_template_material"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("product_templates.id"), index=True)
    material_id: Mapped[str] = mapped_column(String, ForeignKey("materials.id"), index=True)
