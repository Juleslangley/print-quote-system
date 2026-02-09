"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";

type Me = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  active: boolean;
  menu_allow: string[];
  menu_deny: string[];
  visible_menu: string[];
};

const NAV_MENU_ITEMS: { key: string; href: string; label: string }[] = [
  { key: "home", href: "/", label: "Home" },
  { key: "quotes", href: "/quotes", label: "Quotes" },
  { key: "production", href: "/production", label: "Production" },
];

export default function Nav() {
  const path = usePathname();
  const [token, setToken] = useState<string | null>(null);
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    setToken(typeof window !== "undefined" ? localStorage.getItem("token") : null);
  }, []);

  useEffect(() => {
    if (!token) {
      setMe(null);
      return;
    }
    api("/api/me")
      .then((data: Me) => setMe(data))
      .catch(() => setMe(null));
  }, [token]);

  const visibleSet = me?.visible_menu ? new Set(me.visible_menu) : null;
  const navItems = visibleSet
    ? NAV_MENU_ITEMS.filter((item) => visibleSet.has(item.key))
    : NAV_MENU_ITEMS;

  const link = (href: string, label: string) => (
    <Link
      href={href}
      style={{
        padding: "8px 14px",
        borderRadius: 999,
        fontWeight: 500,
        background: path?.startsWith(href) ? "#e5e5e7" : "transparent",
        textDecoration: "none",
        color: "#1d1d1f",
      }}
    >
      {label}
    </Link>
  );

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.8)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid #e5e5e7",
        padding: "12px 24px",
        position: "sticky",
        top: 0,
        zIndex: 100,
        display: "flex",
        gap: 12,
        alignItems: "center",
      }}
    >
      {navItems.map((item) => link(item.href, item.label))}

      <div style={{ marginLeft: "auto", display: "flex", gap: 14, alignItems: "center" }}>
        {token && (visibleSet == null || visibleSet.has("admin")) && (
          <Link
            href="/admin"
            style={{
              padding: "8px 14px",
              borderRadius: 999,
              fontWeight: 500,
              background: path?.startsWith("/admin") ? "#e5e5e7" : "transparent",
              textDecoration: "none",
              color: "#1d1d1f",
            }}
          >
            Admin
          </Link>
        )}
        {token ? (
          <button
            type="button"
            onClick={() => {
              localStorage.removeItem("token");
              window.location.href = "/";
            }}
            style={{
              padding: "8px 14px",
              borderRadius: 999,
              fontWeight: 500,
              border: "none",
              cursor: "pointer",
              background: "#e5e5e7",
              color: "#1d1d1f",
            }}
          >
            Logout
          </button>
        ) : (
          <span style={{ fontSize: 14, color: "#6e6e73" }}>Not logged in</span>
        )}
      </div>
    </div>
  );
}
