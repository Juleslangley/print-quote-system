"""Baseline: users, suppliers, margin_profiles, customers, materials, material_sizes, rates, machines, operations, product_templates, quotes, quote_items

Revision ID: 000_baseline
Revises:
Create Date: 2025-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "000_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ts = sa.DateTime(timezone=True)
    default_ts = sa.text("now()")

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True, server_default=""),
        sa.Column("role", sa.String(), nullable=True, server_default="admin"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("menu_allow", JSONB, nullable=True, server_default="[]"),
        sa.Column("menu_deny", JSONB, nullable=True, server_default="[]"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # --- suppliers (self-FK nullable) ---
    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True, server_default=""),
        sa.Column("phone", sa.String(), nullable=True, server_default=""),
        sa.Column("website", sa.String(), nullable=True, server_default=""),
        sa.Column("contact_person", sa.String(), nullable=True, server_default=""),
        sa.Column("accounts_email", sa.String(), nullable=True, server_default=""),
        sa.Column("account_ref", sa.String(), nullable=True, server_default=""),
        sa.Column("address", sa.String(), nullable=True, server_default=""),
        sa.Column("city", sa.String(), nullable=True, server_default=""),
        sa.Column("postcode", sa.String(), nullable=True, server_default=""),
        sa.Column("country", sa.String(), nullable=True, server_default=""),
        sa.Column("lead_time_days_default", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("notes", sa.String(), nullable=True, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_suppliers_name"), "suppliers", ["name"], unique=True)

    # --- margin_profiles ---
    op.create_table(
        "margin_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("target_margin_pct", sa.Float(), nullable=True, server_default="0.4"),
        sa.Column("min_margin_pct", sa.Float(), nullable=True, server_default="0.25"),
        sa.Column("min_sell_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("rounding", JSONB, nullable=True, server_default='{"mode": "NEAREST", "step": 0.01}'),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_margin_profiles_name"), "margin_profiles", ["name"], unique=True)

    # --- customers ---
    op.create_table(
        "customers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True, server_default=""),
        sa.Column("phone", sa.String(), nullable=True, server_default=""),
        sa.Column("website", sa.String(), nullable=True, server_default=""),
        sa.Column("billing_name", sa.String(), nullable=True, server_default=""),
        sa.Column("billing_email", sa.String(), nullable=True, server_default=""),
        sa.Column("billing_phone", sa.String(), nullable=True, server_default=""),
        sa.Column("billing_address", sa.String(), nullable=True, server_default=""),
        sa.Column("vat_number", sa.String(), nullable=True, server_default=""),
        sa.Column("account_ref", sa.String(), nullable=True, server_default=""),
        sa.Column("notes", sa.String(), nullable=True, server_default=""),
        sa.Column("meta", JSONB, nullable=True, server_default="{}"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("default_margin_profile_id", sa.String(), nullable=True),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["default_margin_profile_id"], ["margin_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_name"), "customers", ["name"], unique=True)

    # --- customer_contacts ---
    op.create_table(
        "customer_contacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=True, server_default=""),
        sa.Column("last_name", sa.String(), nullable=True, server_default=""),
        sa.Column("job_title", sa.String(), nullable=True, server_default=""),
        sa.Column("department", sa.String(), nullable=True, server_default=""),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True, server_default=""),
        sa.Column("phone", sa.String(), nullable=True, server_default=""),
        sa.Column("mobile_phone", sa.String(), nullable=True, server_default=""),
        sa.Column("role", sa.String(), nullable=True, server_default=""),
        sa.Column("notes", sa.String(), nullable=True, server_default=""),
        sa.Column("is_primary", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_contacts_customer_id"), "customer_contacts", ["customer_id"])
    op.create_index(op.f("ix_customer_contacts_name"), "customer_contacts", ["name"])

    # --- customer_contact_methods ---
    op.create_table(
        "customer_contact_methods",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("contact_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True, server_default=""),
        sa.Column("value", sa.String(), nullable=True, server_default=""),
        sa.Column("is_primary", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("can_sms", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("can_whatsapp", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["contact_id"], ["customer_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_contact_methods_contact_id"), "customer_contact_methods", ["contact_id"])

    # --- materials ---
    op.create_table(
        "materials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("nominal_code", sa.String(), nullable=True, server_default=""),
        sa.Column("supplier_product_code", sa.String(), nullable=True, server_default=""),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("supplier", sa.String(), nullable=True, server_default=""),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("cost_per_sheet_gbp", sa.Float(), nullable=True),
        sa.Column("sheet_width_mm", sa.Float(), nullable=True),
        sa.Column("sheet_height_mm", sa.Float(), nullable=True),
        sa.Column("cost_per_lm_gbp", sa.Float(), nullable=True),
        sa.Column("roll_width_mm", sa.Float(), nullable=True),
        sa.Column("min_billable_lm", sa.Float(), nullable=True),
        sa.Column("custom_length_available", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("waste_pct_default", sa.Float(), nullable=True, server_default="0.05"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("meta", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_materials_name"), "materials", ["name"])
    op.create_index(op.f("ix_materials_nominal_code"), "materials", ["nominal_code"])
    op.create_index(op.f("ix_materials_supplier_product_code"), "materials", ["supplier_product_code"])
    op.create_index(op.f("ix_materials_supplier_id"), "materials", ["supplier_id"])

    # --- material_sizes ---
    op.create_table(
        "material_sizes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("material_id", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("width_mm", sa.Float(), nullable=False),
        sa.Column("height_mm", sa.Float(), nullable=True),
        sa.Column("cost_per_sheet_gbp", sa.Float(), nullable=True),
        sa.Column("cost_per_lm_gbp", sa.Float(), nullable=True),
        sa.Column("length_m", sa.Float(), nullable=True),
        sa.Column("custom_length_available", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_material_sizes_material_id"), "material_sizes", ["material_id"])

    # --- rates ---
    op.create_table(
        "rates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("rate_type", sa.String(), nullable=False),
        sa.Column("setup_minutes", sa.Float(), nullable=True, server_default="10"),
        sa.Column("hourly_cost_gbp", sa.Float(), nullable=True, server_default="35"),
        sa.Column("run_speed", JSONB, nullable=True, server_default="{}"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rates_rate_type"), "rates", ["rate_type"])

    # --- machines ---
    op.create_table(
        "machines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("process", sa.String(), nullable=True, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("notes", sa.String(), nullable=True, server_default=""),
        sa.Column("config", JSONB, nullable=True, server_default="{}"),
        sa.Column("meta", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_machines_name"), "machines", ["name"], unique=True)
    op.create_index(op.f("ix_machines_type"), "machines", ["type"])

    # --- machine_rates ---
    op.create_table(
        "machine_rates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("machine_id", sa.String(), nullable=False),
        sa.Column("operation_key", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True, server_default="sqm"),
        sa.Column("cost_per_unit_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("setup_minutes", sa.Float(), nullable=True, server_default="0"),
        sa.Column("setup_cost_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("min_charge_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("notes", sa.String(), nullable=True, server_default=""),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_machine_rates_machine_id"), "machine_rates", ["machine_id"])

    # --- operations ---
    op.create_table(
        "operations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("rate_type", sa.String(), nullable=False),
        sa.Column("calc_model", sa.String(), nullable=False),
        sa.Column("params", JSONB, nullable=True, server_default="{}"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operations_code"), "operations", ["code"], unique=True)
    op.create_index(op.f("ix_operations_name"), "operations", ["name"])
    op.create_index(op.f("ix_operations_rate_type"), "operations", ["rate_type"])
    op.create_index(op.f("ix_operations_calc_model"), "operations", ["calc_model"])

    # --- product_templates ---
    op.create_table(
        "product_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("default_material_id", sa.String(), nullable=False),
        sa.Column("default_machine_id", sa.String(), nullable=True),
        sa.Column("rules", JSONB, nullable=True, server_default="{}"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["default_material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["default_machine_id"], ["machines.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_templates_name"), "product_templates", ["name"])

    # --- template_operations ---
    op.create_table(
        "template_operations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("operation_id", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("params_override", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["product_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "operation_id", name="uq_template_operation"),
    )
    op.create_index(op.f("ix_template_operations_template_id"), "template_operations", ["template_id"])
    op.create_index(op.f("ix_template_operations_operation_id"), "template_operations", ["operation_id"])

    # --- template_allowed_materials ---
    op.create_table(
        "template_allowed_materials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("material_id", sa.String(), nullable=False),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["product_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "material_id", name="uq_template_material"),
    )
    op.create_index(op.f("ix_template_allowed_materials_template_id"), "template_allowed_materials", ["template_id"])
    op.create_index(op.f("ix_template_allowed_materials_material_id"), "template_allowed_materials", ["material_id"])

    # --- template_pricing_rules ---
    op.create_table(
        "template_pricing_rules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("target_margin_pct", sa.Float(), nullable=True),
        sa.Column("min_sell_gbp", sa.Float(), nullable=True),
        sa.Column("sell_multiplier", sa.Float(), nullable=True, server_default="1"),
        sa.Column("margin_profile_id", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("meta", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["product_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["margin_profile_id"], ["margin_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_template_pricing_rules_template_id"), "template_pricing_rules", ["template_id"], unique=True)

    # --- customer_pricing_rules ---
    op.create_table(
        "customer_pricing_rules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("template_id", sa.String(), nullable=True),
        sa.Column("margin_profile_id", sa.String(), nullable=True),
        sa.Column("target_margin_pct", sa.Float(), nullable=True),
        sa.Column("min_sell_gbp", sa.Float(), nullable=True),
        sa.Column("sell_multiplier", sa.Float(), nullable=True, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("meta", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["product_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["margin_profile_id"], ["margin_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_pricing_rules_customer_id"), "customer_pricing_rules", ["customer_id"])

    # --- quotes (no job_id - added by 004) ---
    op.create_table(
        "quotes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("quote_number", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("contact_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default="draft"),
        sa.Column("pricing_version", sa.String(), nullable=False),
        sa.Column("notes_internal", sa.String(), nullable=True, server_default=""),
        sa.Column("subtotal_sell", sa.Float(), nullable=True, server_default="0"),
        sa.Column("vat", sa.Float(), nullable=True, server_default="0"),
        sa.Column("total_sell", sa.Float(), nullable=True, server_default="0"),
        sa.Column("margin_profile_id", sa.String(), nullable=True),
        sa.Column("target_margin_pct", sa.Float(), nullable=True),
        sa.Column("discount_pct", sa.Float(), nullable=True, server_default="0"),
        sa.Column("rounding_override", JSONB, nullable=True, server_default="{}"),
        sa.Column("totals_locked", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["customer_contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["margin_profile_id"], ["margin_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quotes_quote_number"), "quotes", ["quote_number"], unique=True)
    op.create_index(op.f("ix_quotes_customer_id"), "quotes", ["customer_id"])
    op.create_index(op.f("ix_quotes_contact_id"), "quotes", ["contact_id"])

    # --- quote_items ---
    op.create_table(
        "quote_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("quote_id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("width_mm", sa.Float(), nullable=False),
        sa.Column("height_mm", sa.Float(), nullable=False),
        sa.Column("sides", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("options", JSONB, nullable=True, server_default="{}"),
        sa.Column("cost_total", sa.Float(), nullable=True, server_default="0"),
        sa.Column("sell_total", sa.Float(), nullable=True, server_default="0"),
        sa.Column("margin_pct", sa.Float(), nullable=True, server_default="0"),
        sa.Column("calc_snapshot", JSONB, nullable=True, server_default="{}"),
        sa.Column("sell_locked", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("manual_sell_total", sa.Float(), nullable=True),
        sa.Column("manual_discount_pct", sa.Float(), nullable=True, server_default="0"),
        sa.Column("manual_reason", sa.String(), nullable=True, server_default=""),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["product_templates.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quote_items_quote_id"), "quote_items", ["quote_id"])
    op.create_index(op.f("ix_quote_items_template_id"), "quote_items", ["template_id"])


def downgrade() -> None:
    op.drop_table("quote_items")
    op.drop_table("quotes")
    op.drop_table("customer_pricing_rules")
    op.drop_table("template_pricing_rules")
    op.drop_table("template_allowed_materials")
    op.drop_table("template_operations")
    op.drop_table("product_templates")
    op.drop_table("machine_rates")
    op.drop_table("operations")
    op.drop_table("machines")
    op.drop_table("rates")
    op.drop_table("material_sizes")
    op.drop_table("materials")
    op.drop_table("customer_contact_methods")
    op.drop_table("customer_contacts")
    op.drop_table("customers")
    op.drop_table("margin_profiles")
    op.drop_table("suppliers")
    op.drop_table("users")
