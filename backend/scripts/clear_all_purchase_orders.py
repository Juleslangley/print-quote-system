"""One-off: delete all purchase_order_lines, purchase_orders, and reset po_sequences. Run from backend dir."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.core.db import SessionLocal
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.purchase_order import PurchaseOrder

def main():
    db = SessionLocal()
    try:
        db.query(PurchaseOrderLine).delete(synchronize_session=False)
        db.query(PurchaseOrder).delete(synchronize_session=False)
        db.execute(text("DELETE FROM po_sequences"))
        db.execute(text("INSERT INTO po_sequences (key, last_number) VALUES ('purchase_order', 0)"))
        db.commit()
        print("Done: all purchase orders and lines removed, PO sequence reset to 0.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
