"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, clearToken } from "@/lib/api";

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
  { key: "packing", href: "/packing", label: "Packing" },
];

export default function Nav() {
  const path = usePathname();
  const [token, setToken] = useState<string | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [authUnavailable, setAuthUnavailable] = useState(false);

  const readToken = () => setToken(typeof window !== "undefined" ? localStorage.getItem("token") : null);

  useEffect(() => {
    readToken();
    window.addEventListener("auth-change", readToken);
    return () => window.removeEventListener("auth-change", readToken);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || process.env.NODE_ENV !== "development") return;
    (window as unknown as { __whoBlocksNav?: () => { tag: string; id: string; class: string } | null }).__whoBlocksNav = () => {
      const el = document.elementFromPoint(window.innerWidth - 30, 20);
      return el ? { tag: el.tagName, id: el.id, class: el.className } : null;
    };
  }, []);

  useEffect(() => {
    if (!token) {
      setMe(null);
      setAuthUnavailable(false);
      return;
    }
    setAuthUnavailable(false);
    api<Me>("/api/me")
      .then((data) => {
        setMe(data);
        setAuthUnavailable(false);
      })
      .catch(() => {
        setMe(null);
        setAuthUnavailable(true);
      });
  }, [token]);

  const visibleSet = me?.visible_menu ? new Set(me.visible_menu) : null;
  const navItems = visibleSet
    ? NAV_MENU_ITEMS.filter((item) => visibleSet.has(item.key))
    : NAV_MENU_ITEMS;

  return (
    <>
      {authUnavailable && (
        <div
          style={{
            background: "#f59e0b",
            color: "#000",
            padding: "8px 16px",
            textAlign: "center",
            fontSize: 13,
          }}
        >
          Backend/auth unavailable – menu items hidden. Start backend on :8000 and log in.
        </div>
      )}
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
      {navItems.map((item) => (
        <Link
          key={item.key}
          href={item.href}
          style={{
            padding: "8px 14px",
            borderRadius: 999,
            fontWeight: 500,
            background: path?.startsWith(item.href) ? "#e5e5e7" : "transparent",
            textDecoration: "none",
            color: "#1d1d1f",
          }}
        >
          {item.label}
        </Link>
      ))}

      <div style={{ marginLeft: "auto", display: "flex", gap: 14, alignItems: "center" }}>
        {token && (
          <Link
            href="/insights"
            style={{
              padding: "8px 14px",
              borderRadius: 999,
              fontWeight: 500,
              background: path?.startsWith("/insights") ? "#e5e5e7" : "transparent",
              textDecoration: "none",
              color: "#1d1d1f",
            }}
          >
            Insights
          </Link>
        )}
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
              clearToken();
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
    </>
  );
}
