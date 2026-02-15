"use client";

import PurchaseOrderList from "../../_components/PurchaseOrderList";

export default function PurchaseOrdersPage() {
  return (
    <PurchaseOrderList
      fromMaterials
      title="Purchase orders"
      subtitle="Create and manage purchase orders to suppliers."
    />
  );
}
