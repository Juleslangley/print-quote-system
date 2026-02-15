from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from sqlalchemy.orm import Session
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.supplier import Supplier


def build_po_pdf(db: Session, po: PurchaseOrder) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    supp_name = supplier.name if supplier else po.supplier_id
    supp_contact = []
    if supplier:
        if supplier.email:
            supp_contact.append(supplier.email)
        if supplier.phone:
            supp_contact.append(supplier.phone)
    supp_contact_str = " | ".join(supp_contact) if supp_contact else ""

    po_label = po.po_number if po.po_number and not (isinstance(po.po_number, str) and po.po_number.startswith("DRAFT-")) else "Draft"
    story.append(Paragraph(f"<b>Purchase Order {po_label}</b>", styles["Title"]))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("<b>Supplier</b>", styles["Heading2"]))
    story.append(Paragraph(supp_name, styles["Normal"]))
    if supp_contact_str:
        story.append(Paragraph(supp_contact_str, styles["Normal"]))
    story.append(Spacer(1, 4*mm))

    if po.delivery_name or po.delivery_address:
        story.append(Paragraph("<b>Delivery</b>", styles["Heading2"]))
        if po.delivery_name:
            story.append(Paragraph(po.delivery_name, styles["Normal"]))
        if po.delivery_address:
            story.append(Paragraph(po.delivery_address.replace("\n", "<br/>"), styles["Normal"]))
        story.append(Spacer(1, 4*mm))

    if po.notes:
        story.append(Paragraph(f"<b>Notes</b>: {po.notes}", styles["Normal"]))
        story.append(Spacer(1, 4*mm))

    lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po.id, PurchaseOrderLine.active.is_(True))
        .order_by(PurchaseOrderLine.sort_order.asc(), PurchaseOrderLine.id.asc())
        .all()
    )

    data = [["Description", "Supplier code", "Qty", "UOM", "Unit cost", "Line total"]]
    for line in lines:
        data.append([
            line.description or "—",
            line.supplier_product_code or "—",
            str(line.qty),
            line.uom or "—",
            f"£{line.unit_cost_gbp:.2f}",
            f"£{line.line_total_gbp:.2f}",
        ])

    if len(data) > 1:
        t = Table(data, colWidths=[50*mm, 30*mm, 18*mm, 18*mm, 25*mm, 25*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 6*mm))

    story.append(Paragraph(f"<b>Subtotal</b>: £{po.subtotal_gbp:.2f}", styles["Normal"]))
    story.append(Paragraph(f"<b>VAT (20%)</b>: £{po.vat_gbp:.2f}", styles["Normal"]))
    story.append(Paragraph(f"<b>Total</b>: £{po.total_gbp:.2f}", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
