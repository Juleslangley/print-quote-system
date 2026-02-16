"""One-off: delete all purchase_order_lines and purchase_orders. Run from backend dir."""
import sys
sys.path.insert(0, ".")
from app.core.db import SessionLocal
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.purchase_order import PurchaseOrder

def main():
    db = SessionLocal()
    try:
        db.query(PurchaseOrderLine).delete(synchronize_session=False)
        db.query(PurchaseOrder).delete(synchronize_session=False)
        db.commit()
        print("Done: all purchase orders and lines removed.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
