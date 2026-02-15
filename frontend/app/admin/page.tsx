"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { OVERHEAD_SUMMARY, formatCurrency } from "@/lib/adminOverheads";

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
  { key: "admin.overheads", href: "/admin/overheads", label: "Overheads" },
  { key: "admin.purchase_orders", href: "/admin/purchase-orders", label: "Purchase orders" },
  { key: "admin.packing", href: "/admin/packing", label: "Packing Proof" },
];

export default function AdminHome() {
  const [backupLoading, setBackupLoading] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [restoreMessage, setRestoreMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Show all admin links; backend returns 403 if user has no access to a route
  const links = ADMIN_LINKS;

  const handleBackup = async () => {
    setBackupLoading(true);
    setRestoreMessage(null);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const res = await fetch("/api/backup", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const t = await res.text();
        let msg = t;
        try {
          const j = JSON.parse(t);
          if (typeof j?.detail === "string") msg = j.detail;
        } catch {}
        throw new Error(msg);
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `quote-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setRestoreMessage(e instanceof Error ? e.message : "Backup failed");
    } finally {
      setBackupLoading(false);
    }
  };

  const handleRestore = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setRestoreLoading(true);
    setRestoreMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const res = await fetch("/api/backup/restore", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      const text = await res.text();
      if (!res.ok) {
        let msg = text;
        try {
          const j = JSON.parse(text);
          if (typeof j?.detail === "string") msg = j.detail;
        } catch {}
        throw new Error(msg);
      }
      setRestoreMessage("Restore complete. Reload the page to see restored data.");
    } catch (err) {
      setRestoreMessage(err instanceof Error ? err.message : "Restore failed");
    } finally {
      setRestoreLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div>
      <h1>Admin</h1>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: "1rem", marginBottom: 8 }}>Data backup &amp; restore</h2>
        <p style={{ color: "#555", marginBottom: 8 }}>
          Save all app data (materials, customers, POs, etc.) to a file, or restore from a previous backup.
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={handleBackup}
            disabled={backupLoading}
            style={{
              padding: "8px 16px",
              cursor: backupLoading ? "not-allowed" : "pointer",
              background: "#0066cc",
              color: "white",
              border: "none",
              borderRadius: 4,
            }}
          >
            {backupLoading ? "Saving…" : "Backup data"}
          </button>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleRestore}
              disabled={restoreLoading}
              style={{ display: "none" }}
            />
            <span
              style={{
                padding: "8px 16px",
                background: restoreLoading ? "#999" : "#28a745",
                color: "white",
                borderRadius: 4,
                pointerEvents: restoreLoading ? "none" : "auto",
              }}
            >
              {restoreLoading ? "Restoring…" : "Restore data"}
            </span>
          </label>
        </div>
        {restoreMessage && (
          <p style={{ marginTop: 8, color: restoreMessage.startsWith("Restore complete") ? "green" : "#c00" }}>
            {restoreMessage}
          </p>
        )}
      </section>

      <section className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: "1rem", marginBottom: 8 }}>Admin overheads</h2>
        <p className="subtle" style={{ marginBottom: 12 }}>
          Your monthly overhead dataset is now available in-app.
        </p>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 12 }}>
          <div>
            <div className="subtle">Annual total</div>
            <div style={{ fontWeight: 700 }}>{formatCurrency(OVERHEAD_SUMMARY.annualTotal)}</div>
          </div>
          <div>
            <div className="subtle">Comparison total</div>
            <div style={{ fontWeight: 700 }}>{formatCurrency(OVERHEAD_SUMMARY.comparisonTotal)}</div>
          </div>
          <div>
            <div className="subtle">Average per month</div>
            <div style={{ fontWeight: 700 }}>{formatCurrency(OVERHEAD_SUMMARY.monthlyAverage)}</div>
          </div>
        </div>
        <Link
          href="/admin/overheads"
          style={{
            display: "inline-block",
            padding: "8px 14px",
            borderRadius: 999,
            background: "#0066cc",
            color: "#fff",
            textDecoration: "none",
            fontWeight: 500,
          }}
        >
          Open Overheads section
        </Link>
      </section>

      <h2 style={{ fontSize: "1rem", marginBottom: 8 }}>Admin links</h2>
      <ul style={{ listStyle: "none", paddingLeft: 0 }}>
        {links.map(({ href, label }) => (
          <li key={href} style={{ marginBottom: 8 }}>
            <Link
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
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
