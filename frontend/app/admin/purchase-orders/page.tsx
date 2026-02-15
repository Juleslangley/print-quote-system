"use client";

import PurchaseOrderList from "../../_components/PurchaseOrderList";

export default function AdminPurchaseOrdersPage() {
  return (
    <div>
      <PurchaseOrderList
        title="Purchase Orders"
        subtitle="Create and manage purchase orders to suppliers."
      />
    </div>
  );
}
