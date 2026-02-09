"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

const ADMIN_LINKS: { key: string; href: string; label: string }[] = [
  { key: "admin.customers", href: "/admin/customers", label: "Customers" },
  { key: "admin.users", href: "/admin/users", label: "Users" },
  { key: "admin.materials", href: "/admin/materials", label: "Materials (view + edit)" },
  { key: "admin.suppliers", href: "/admin/suppliers", label: "Suppliers" },
  { key: "admin.machines", href: "/admin/machines", label: "Machines" },
  { key: "admin.rates", href: "/admin/rates", label: "Rates (view + edit)" },
  { key: "admin.operations", href: "/admin/operations", label: "Operations library" },
  { key: "admin.templates", href: "/admin/templates", label: "Templates + operation order" },
  { key: "admin.margins", href: "/admin/margins", label: "Margin profiles" },
  { key: "admin.purchase_orders", href: "/admin/purchase-orders", label: "Purchase orders" },
  { key: "admin.invoices", href: "/admin/invoices", label: "Supplier invoices" },
];

type Me = { visible_menu?: string[] };

export default function AdminHome() {
  const [visibleSet, setVisibleSet] = useState<Set<string> | null>(null);

  useEffect(() => {
    api("/api/me")
      .then((data: Me) => {
        setVisibleSet(data.visible_menu ? new Set(data.visible_menu) : new Set());
      })
      .catch(() => setVisibleSet(new Set()));
  }, []);

  const links = visibleSet
    ? ADMIN_LINKS.filter((item) => visibleSet.has(item.key))
    : ADMIN_LINKS;

  return (
    <div>
      <h1>Admin</h1>
      <ul style={{ listStyle: "none", paddingLeft: 0 }}>
        {links.map(({ href, label }) => (
          <li key={href} style={{ marginBottom: 8 }}>
            <a
              href={href}
              style={{
                display: "block",
                padding: "8px 0",
                color: "#0066cc",
                textDecoration: "underline",
                cursor: "pointer",
              }}
            >
              {label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
