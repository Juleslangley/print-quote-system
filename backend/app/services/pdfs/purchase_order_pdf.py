from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.supplier import Supplier
from app.services.po_template import get_po_template_config


def _fmt_date(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d %b %Y")


def _fmt_qty(value: float | int | None) -> str:
    if value is None:
        return "0"
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return "0"
    if as_float.is_integer():
        return str(int(as_float))
    return f"{as_float:.2f}".rstrip("0").rstrip(".")


def _as_html(value: str) -> str:
    return escape(value).replace("\n", "<br/>")


def _is_light_hex(hex_color: str) -> bool:
    clean = hex_color.lstrip("#")
    if len(clean) != 6:
        return False
    try:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
    except ValueError:
        return False
    luminance = (0.299 * r) + (0.587 * g) + (0.114 * b)
    return luminance > 180


def build_po_pdf(db: Session, po: PurchaseOrder) -> bytes:
    cfg = get_po_template_config(db)
    accent_hex = cfg.get("accent_color", "#1F2937")
    accent = colors.HexColor(accent_hex)
    header_text_color = colors.black if _is_light_hex(accent_hex) else colors.whitesmoke

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "POTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=accent,
        spaceAfter=2 * mm,
    )
    heading_style = ParagraphStyle(
        "POHeading",
        parent=styles["Heading4"],
        textColor=accent,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        spaceBefore=2 * mm,
        spaceAfter=1 * mm,
    )
    normal_style = ParagraphStyle(
        "PONormal",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=12,
    )

    supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    supplier_name = supplier.name if supplier else po.supplier_id
    supplier_contact = []
    if supplier and cfg.get("show_supplier_contact", True):
        if supplier.email:
            supplier_contact.append(supplier.email)
        if supplier.phone:
            supplier_contact.append(supplier.phone)

    story.append(Paragraph(f"<b>{_as_html(cfg.get('document_title', 'PURCHASE ORDER'))}</b>", title_style))
    if cfg.get("header_note"):
        story.append(Paragraph(_as_html(cfg["header_note"]), normal_style))
        story.append(Spacer(1, 2 * mm))

    company_lines = [cfg.get("company_name", "").strip()]
    if cfg.get("company_address"):
        company_lines.extend([x.strip() for x in str(cfg["company_address"]).splitlines() if x.strip()])
    if cfg.get("company_email"):
        company_lines.append(f"Email: {cfg['company_email']}")
    if cfg.get("company_phone"):
        company_lines.append(f"Tel: {cfg['company_phone']}")
    if cfg.get("company_vat"):
        company_lines.append(str(cfg["company_vat"]))
    company_block = "<br/>".join(_as_html(x) for x in company_lines if x)

    meta_block = "<br/>".join(
        [
            f"<b>PO Number:</b> {_as_html(po.po_number)}",
            f"<b>Order date:</b> {_as_html(_fmt_date(po.order_date))}",
            f"<b>Required by:</b> {_as_html(_fmt_date(po.required_by))}",
            f"<b>Expected by:</b> {_as_html(_fmt_date(po.expected_by))}",
            f"<b>Status:</b> {_as_html(po.status)}",
        ]
    )
    header_data = [[Paragraph(company_block or " ", normal_style), Paragraph(meta_block, normal_style)]]
    header_table = Table(header_data, colWidths=[108 * mm, 62 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Supplier</b>", heading_style))
    story.append(Paragraph(_as_html(supplier_name), normal_style))
    if supplier_contact:
        story.append(Paragraph(_as_html(" | ".join(supplier_contact)), normal_style))
    story.append(Spacer(1, 2 * mm))

    if cfg.get("show_delivery_block", True) and (po.delivery_name or po.delivery_address):
        story.append(Paragraph("<b>Deliver To</b>", heading_style))
        if po.delivery_name:
            story.append(Paragraph(_as_html(po.delivery_name), normal_style))
        if po.delivery_address:
            story.append(Paragraph(_as_html(po.delivery_address), normal_style))
        story.append(Spacer(1, 2 * mm))

    if cfg.get("show_notes_block", True) and po.notes:
        story.append(Paragraph("<b>Notes</b>", heading_style))
        story.append(Paragraph(_as_html(po.notes), normal_style))
        story.append(Spacer(1, 2 * mm))

    if cfg.get("show_internal_notes", False) and po.internal_notes:
        story.append(Paragraph("<b>Internal notes</b>", heading_style))
        story.append(Paragraph(_as_html(po.internal_notes), normal_style))
        story.append(Spacer(1, 2 * mm))

    lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po.id, PurchaseOrderLine.active.is_(True))
        .order_by(PurchaseOrderLine.sort_order.asc(), PurchaseOrderLine.id.asc())
        .all()
    )
    data = [["Description", "Supplier code", "Qty", "UOM", "Unit cost", "Line total"]]
    for line in lines:
        data.append(
            [
                line.description or "—",
                line.supplier_product_code or "—",
                _fmt_qty(line.qty),
                line.uom or "—",
                f"£{line.unit_cost_gbp:.2f}",
                f"£{line.line_total_gbp:.2f}",
            ]
        )

    line_table = Table(data, colWidths=[62 * mm, 28 * mm, 16 * mm, 16 * mm, 24 * mm, 24 * mm])
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), header_text_color),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if cfg.get("table_style") == "clean":
        table_style.append(("LINEBELOW", (0, 0), (-1, 0), 0.9, accent))
        if len(data) > 1:
            table_style.append(("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#D1D5DB")))
    else:
        table_style.append(("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9CA3AF")))
    if cfg.get("show_zebra_rows", True) and len(data) > 1:
        table_style.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]))
    line_table.setStyle(TableStyle(table_style))
    story.append(line_table)
    story.append(Spacer(1, 3 * mm))

    totals_table = Table(
        [
            ["Subtotal", f"£{po.subtotal_gbp:.2f}"],
            ["VAT (20%)", f"£{po.vat_gbp:.2f}"],
            ["Total", f"£{po.total_gbp:.2f}"],
        ],
        colWidths=[140 * mm, 30 * mm],
    )
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEABOVE", (0, 2), (-1, 2), 0.8, colors.HexColor("#9CA3AF")),
            ]
        )
    )
    story.append(totals_table)

    terms_rows: list[str] = []
    if cfg.get("payment_terms"):
        terms_rows.append(cfg["payment_terms"])
    if cfg.get("delivery_terms"):
        terms_rows.append(cfg["delivery_terms"])
    if terms_rows:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("<b>Terms</b>", heading_style))
        for row in terms_rows:
            story.append(Paragraph(_as_html(row), normal_style))
    if cfg.get("footer_note"):
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(_as_html(cfg["footer_note"]), normal_style))

    doc.build(story)
    return buffer.getvalue()
