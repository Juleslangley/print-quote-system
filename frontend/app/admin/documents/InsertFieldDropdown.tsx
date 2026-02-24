"use client";

export const JINJA_FIELDS: Record<string, { label: string; token: string }[]> = {
  purchase_order: [
    { label: "PO number", token: "{{ po.po_number }}" },
    { label: "Order date", token: "{{ po.order_date.strftime('%d/%m/%Y') if po.order_date else '' }}" },
    { label: "Required by", token: "{{ po.required_by.strftime('%d/%m/%Y') if po.required_by else '' }}" },
    { label: "Expected by", token: "{{ po.expected_by.strftime('%d/%m/%Y') if po.expected_by else '' }}" },
    { label: "Supplier name", token: "{{ supplier.name if supplier else '' }}" },
    { label: "Supplier address", token: "{{ supplier.address if supplier else '' }}" },
    { label: "Supplier city", token: "{{ supplier.city if supplier else '' }}" },
    { label: "Supplier postcode", token: "{{ supplier.postcode if supplier else '' }}" },
    { label: "Delivery name", token: "{{ delivery.name }}" },
    { label: "Delivery address", token: "{{ delivery.address }}" },
    { label: "Notes", token: "{{ notes }}" },
    { label: "Terms", token: "{{ terms }}" },
    { label: "Subtotal", token: "£{{ '%.2f'|format(totals.subtotal) }}" },
    { label: "VAT", token: "£{{ '%.2f'|format(totals.vat) }}" },
    { label: "Total", token: "£{{ '%.2f'|format(totals.total) }}" },
  ],
  quote: [
    { label: "Quote number", token: "{{ quote.quote_number }}" },
    { label: "Subtotal", token: "£{{ '%.2f'|format(quote.subtotal_sell or 0) }}" },
    { label: "VAT", token: "£{{ '%.2f'|format(quote.vat or 0) }}" },
    { label: "Total", token: "£{{ '%.2f'|format(quote.total_sell or 0) }}" },
  ],
  invoice: [
    { label: "PO number", token: "{{ po.po_number }}" },
    { label: "Order date", token: "{{ po.order_date.strftime('%d/%m/%Y') if po.order_date else '' }}" },
    { label: "Supplier name", token: "{{ supplier.name if supplier else '' }}" },
    { label: "Total", token: "£{{ '%.2f'|format(po.total_gbp or 0) }}" },
  ],
  credit_note: [
    { label: "PO number", token: "{{ po.po_number }}" },
    { label: "Total", token: "£{{ '%.2f'|format(po.total_gbp or 0) }}" },
  ],
  production_order: [
    { label: "Job number", token: "{{ job.job_no }}" },
    { label: "Job title", token: "{{ job.title }}" },
    { label: "Barcode SVG", token: "{{ job.barcode_svg }}" },
  ],
};

