#!/usr/bin/env python3
"""
Regression script: create 3 purchase orders and verify:
- No custom PO sequence errors
- po_numbers are PO0000001, PO0000002, PO0000003 (or continue correctly)
- Unique constraint on po_number holds
Run from backend dir: python scripts/test_po_regression.py
"""
import sys
sys.path.insert(0, ".")

from app.core.db import SessionLocal
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.supplier import Supplier
def main():
    db = SessionLocal()
    try:
        supplier = db.query(Supplier).first()
        if not supplier:
            print("ERROR: No supplier in DB. Create a supplier first.")
            sys.exit(1)

        # Create 3 purchase orders (no id/po_number passed - set by DB and after_insert)
        created = []
        for i in range(3):
            po = PurchaseOrder(
                supplier_id=supplier.id,
                status="draft",
                delivery_name="",
                delivery_address="",
                notes="",
                internal_notes="",
            )
            db.add(po)
            db.flush()
            created.append(po)
            print(f"  Created PO id={po.id} po_number={po.po_number}")

        db.commit()
        db.refresh(created[0])
        db.refresh(created[1])
        db.refresh(created[2])

        # Verify
        po_numbers = [po.po_number for po in created]
        ids = [po.id for po in created]
        expected = [f"PO{i:07d}" for i in ids]

        if po_numbers != expected:
            print(f"ERROR: Expected po_numbers {expected}, got {po_numbers}")
            sys.exit(1)
        if len(set(po_numbers)) != 3:
            print(f"ERROR: po_numbers not unique: {po_numbers}")
            sys.exit(1)

        print("OK: No sequence errors, po_numbers correct, unique constraint holds")

        # Cleanup
        for po in created:
            db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).delete(synchronize_session=False)
            db.delete(po)
        db.commit()
        print("OK: Cleanup done")
    finally:
        db.close()


if __name__ == "__main__":
    main()
