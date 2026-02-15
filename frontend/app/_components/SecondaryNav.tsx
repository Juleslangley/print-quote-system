"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Me = {
  visible_menu: string[];
};

const SECONDARY_TABS: { key: string; href: string; label: string; menuKey?: string }[] = [
  { key: "dashboard", href: "/", label: "Dashboard" },
  { key: "customers", href: "/customers", label: "Customers", menuKey: "customers" },
  { key: "suppliers", href: "/suppliers", label: "Suppliers", menuKey: "admin.suppliers" },
  { key: "materials", href: "/materials", label: "Materials", menuKey: "materials" },
  { key: "purchase_orders", href: "/purchase-orders", label: "Purchase orders", menuKey: "admin.purchase_orders" },
];

export default function SecondaryNav() {
  const path = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const readToken = () => setToken(typeof window !== "undefined" ? localStorage.getItem("token") : null);
  useEffect(() => {
    readToken();
    window.addEventListener("auth-change", readToken);
    return () => window.removeEventListener("auth-change", readToken);
  }, []);

  useEffect(() => {
    if (!token || typeof window === "undefined") {
      setMe(null);
      return;
    }
    api<Me>("/api/me")
      .then((data) => setMe(data))
      .catch(() => setMe(null));
  }, [token]);

  const visibleSet = me?.visible_menu ? new Set(me.visible_menu) : null;
  const showMaterialsTab = visibleSet === null || visibleSet.has("materials") || visibleSet.has("admin.materials");
  const showCustomersTab = visibleSet === null || visibleSet.has("customers") || visibleSet.has("admin.customers");
  const showSuppliersTab = visibleSet === null || visibleSet.has("admin.suppliers");
  const showPurchaseOrdersTab = visibleSet === null || visibleSet.has("admin.purchase_orders");
  const tabs = SECONDARY_TABS.filter((t) => {
    if (t.menuKey === "materials") return showMaterialsTab;
    if (t.menuKey === "customers") return showCustomersTab;
    if (t.menuKey === "admin.suppliers") return showSuppliersTab;
    if (t.menuKey === "admin.purchase_orders") return showPurchaseOrdersTab;
    return true;
  });

  return (
    <div
      style={{
        display: "flex",
        gap: 12,
        alignItems: "center",
        padding: "10px 0 14px",
        borderBottom: "1px solid #e5e5e7",
        marginBottom: 16,
      }}
    >
      {tabs.map((tab) => {
        const isActive = tab.href === "/" ? path === "/" : path?.startsWith(tab.href);
        return (
          <Link
            key={tab.key}
            href={tab.href}
            style={{
              padding: "8px 14px",
              borderRadius: 999,
              fontWeight: 500,
              background: isActive ? "#e5e5e7" : "transparent",
              textDecoration: "none",
              color: "#1d1d1f",
            }}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
