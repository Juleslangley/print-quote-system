"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";

type POConfig = {
  template_name: string;
  document_title: string;
  company_name: string;
  company_address: string;
  company_email: string;
  company_phone: string;
  company_vat: string;
  header_note: string;
  payment_terms: string;
  delivery_terms: string;
  footer_note: string;
  accent_color: string;
  table_style: "boxed" | "clean";
  show_supplier_contact: boolean;
  show_delivery_block: boolean;
  show_notes_block: boolean;
  show_internal_notes: boolean;
  show_zebra_rows: boolean;
};

type POTemplateResponse = {
  id: string | null;
  key: string;
  name: string;
  config: POConfig;
  default_config: POConfig;
  updated_at: string | null;
};

type POListItem = {
  id: string;
  po_number: string;
  status: string;
  order_date: string | null;
};

const BASE_CONFIG: POConfig = {
  template_name: "Standard Industry PO",
  document_title: "PURCHASE ORDER",
  company_name: "Your Company Name Ltd",
  company_address: "Company Address Line 1\nCompany Address Line 2\nPostcode",
  company_email: "accounts@your-company.com",
  company_phone: "+44 (0)0000 000000",
  company_vat: "VAT: GB123456789",
  header_note: "Please supply in accordance with this purchase order.",
  payment_terms: "Payment terms: 30 days end of month unless agreed otherwise.",
  delivery_terms: "Delivery terms: deliver to the address on this PO unless agreed in writing.",
  footer_note: "Please acknowledge receipt of this PO and confirm your expected delivery date.",
  accent_color: "#1F2937",
  table_style: "boxed",
  show_supplier_contact: true,
  show_delivery_block: true,
  show_notes_block: true,
  show_internal_notes: false,
  show_zebra_rows: true,
};

function coerceConfig(raw: any): POConfig {
  const cfg = { ...BASE_CONFIG, ...(raw || {}) };
  cfg.table_style = cfg.table_style === "clean" ? "clean" : "boxed";
  if (typeof cfg.accent_color !== "string" || !/^#[0-9a-fA-F]{6}$/.test(cfg.accent_color)) {
    cfg.accent_color = BASE_CONFIG.accent_color;
  } else {
    cfg.accent_color = cfg.accent_color.toUpperCase();
  }
  return cfg;
}

export default function AdminPOTemplatePage() {
  const [err, setErr] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);

  const [config, setConfig] = useState<POConfig>(BASE_CONFIG);
  const [defaultConfig, setDefaultConfig] = useState<POConfig>(BASE_CONFIG);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const [poOptions, setPoOptions] = useState<POListItem[]>([]);
  const [previewPoId, setPreviewPoId] = useState("");
  const [openingPreview, setOpeningPreview] = useState(false);

  async function load() {
    setErr("");
    setNotice("");
    setLoading(true);
    try {
      const [templateRes, poList] = await Promise.all([
        api<POTemplateResponse>("/api/po-template"),
        api<POListItem[]>("/api/purchase-orders"),
      ]);
      const nextConfig = coerceConfig(templateRes?.config);
      const nextDefault = coerceConfig(templateRes?.default_config);
      setConfig(nextConfig);
      setDefaultConfig(nextDefault);
      setUpdatedAt(templateRes?.updated_at || null);
      const options = poList ?? [];
      setPoOptions(options);
      if (options.length && !previewPoId) setPreviewPoId(options[0].id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function setField<K extends keyof POConfig>(key: K, value: POConfig[K]) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  async function saveTemplate() {
    setSaving(true);
    setErr("");
    setNotice("");
    try {
      const res = await api<POTemplateResponse>("/api/po-template", {
        method: "PUT",
        body: JSON.stringify({ config }),
      });
      setConfig(coerceConfig(res?.config));
      setDefaultConfig(coerceConfig(res?.default_config));
      setUpdatedAt(res?.updated_at || null);
      setNotice("PO template saved. New PDFs will use this layout.");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function resetTemplate() {
    if (!confirm("Reset the PO template to the standard industry default?")) return;
    setResetting(true);
    setErr("");
    setNotice("");
    try {
      const res = await api<POTemplateResponse>("/api/po-template/reset", {
        method: "POST",
      });
      setConfig(coerceConfig(res?.config));
      setDefaultConfig(coerceConfig(res?.default_config));
      setUpdatedAt(res?.updated_at || null);
      setNotice("PO template reset to default.");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setResetting(false);
    }
  }

  async function openPdfPreview() {
    if (!previewPoId) {
      setErr("Create a purchase order first to preview the PDF.");
      return;
    }
    setOpeningPreview(true);
    setErr("");
    setNotice("");
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const res = await fetch(`/api/purchase-orders/${previewPoId}.pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Failed to open PDF preview");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e: any) {
      setErr(e?.message || "Preview failed");
    } finally {
      setOpeningPreview(false);
    }
  }

  const previewSummary = useMemo(() => {
    return [
      config.company_name || "Company name",
      config.company_email || "company@email.example",
      config.company_phone || "phone",
      config.company_vat || "VAT details",
    ].filter(Boolean).join(" | ");
  }, [config.company_name, config.company_email, config.company_phone, config.company_vat]);

  if (loading) return <div className="subtle">Loading PO template...</div>;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <a href="/admin" className="subtle" style={{ textDecoration: "underline" }}>&lt;- Admin</a>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>PO Template Editor</h1>
          <div className="subtle">Define how Purchase Order PDFs look and save a reusable standard template.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" onClick={load}>Reload</button>
          <button type="button" className="primary" onClick={saveTemplate} disabled={saving}>
            {saving ? "Saving..." : "Save Template"}
          </button>
        </div>
      </div>

      {updatedAt && (
        <div className="subtle" style={{ marginBottom: 10 }}>
          Last updated: {new Date(updatedAt).toLocaleString()}
        </div>
      )}

      {err && (
        <div className="card" style={{ borderColor: "#c00", marginBottom: 12, whiteSpace: "pre-wrap" }}>
          {err}
        </div>
      )}
      {notice && (
        <div className="card" style={{ borderColor: "#86efac", background: "#f0fdf4", marginBottom: 12, whiteSpace: "pre-wrap" }}>
          {notice}
        </div>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="row">
          <div className="col">
            <label className="subtle">Template name</label>
            <input
              value={config.template_name}
              onChange={(e) => setField("template_name", e.target.value)}
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div className="col">
            <label className="subtle">Document title</label>
            <input
              value={config.document_title}
              onChange={(e) => setField("document_title", e.target.value)}
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div className="col">
            <label className="subtle">Accent color</label>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
              <input
                type="color"
                value={config.accent_color}
                onChange={(e) => setField("accent_color", e.target.value.toUpperCase())}
                style={{ width: 48, height: 36, padding: 2 }}
              />
              <input
                value={config.accent_color}
                onChange={(e) => setField("accent_color", e.target.value)}
                style={{ flex: 1 }}
              />
            </div>
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <div className="col">
            <label className="subtle">Table style</label>
            <select
              value={config.table_style}
              onChange={(e) => setField("table_style", e.target.value === "clean" ? "clean" : "boxed")}
              style={{ width: "100%", marginTop: 4 }}
            >
              <option value="boxed">Boxed grid (typical printed PO style)</option>
              <option value="clean">Clean lines</option>
            </select>
          </div>
          <div className="col">
            <label style={{ display: "block", marginTop: 26 }}>
              <input
                type="checkbox"
                checked={config.show_zebra_rows}
                onChange={(e) => setField("show_zebra_rows", e.target.checked)}
              />{" "}
              Zebra rows on line items
            </label>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Company block</h3>
        <div className="row">
          <div className="col">
            <label className="subtle">Company name</label>
            <input value={config.company_name} onChange={(e) => setField("company_name", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div className="col">
            <label className="subtle">Company email</label>
            <input value={config.company_email} onChange={(e) => setField("company_email", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div className="col">
            <label className="subtle">Company phone</label>
            <input value={config.company_phone} onChange={(e) => setField("company_phone", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <div className="col">
            <label className="subtle">Company address</label>
            <textarea rows={4} value={config.company_address} onChange={(e) => setField("company_address", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div className="col">
            <label className="subtle">VAT / registration line</label>
            <input value={config.company_vat} onChange={(e) => setField("company_vat", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Notes and terms</h3>
        <div style={{ marginBottom: 10 }}>
          <label className="subtle">Header note</label>
          <textarea rows={2} value={config.header_note} onChange={(e) => setField("header_note", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label className="subtle">Payment terms</label>
          <textarea rows={2} value={config.payment_terms} onChange={(e) => setField("payment_terms", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label className="subtle">Delivery terms</label>
          <textarea rows={2} value={config.delivery_terms} onChange={(e) => setField("delivery_terms", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
        </div>
        <div>
          <label className="subtle">Footer note</label>
          <textarea rows={2} value={config.footer_note} onChange={(e) => setField("footer_note", e.target.value)} style={{ width: "100%", marginTop: 4 }} />
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Visibility controls</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <label><input type="checkbox" checked={config.show_supplier_contact} onChange={(e) => setField("show_supplier_contact", e.target.checked)} /> Show supplier email/phone on PO</label>
          <label><input type="checkbox" checked={config.show_delivery_block} onChange={(e) => setField("show_delivery_block", e.target.checked)} /> Show delivery block</label>
          <label><input type="checkbox" checked={config.show_notes_block} onChange={(e) => setField("show_notes_block", e.target.checked)} /> Show supplier notes block</label>
          <label><input type="checkbox" checked={config.show_internal_notes} onChange={(e) => setField("show_internal_notes", e.target.checked)} /> Show internal notes (usually off for supplier-facing PO)</label>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16, background: "#fafafa" }}>
        <h3 style={{ marginTop: 0 }}>Quick visual summary</h3>
        <p style={{ margin: "0 0 8px" }}><strong>{config.document_title || "PURCHASE ORDER"}</strong></p>
        <p className="subtle" style={{ margin: "0 0 8px" }}>{previewSummary}</p>
        {config.header_note && <p style={{ margin: "0 0 8px" }}>{config.header_note}</p>}
        <p className="subtle" style={{ margin: 0 }}>
          Table style: {config.table_style} | Zebra rows: {config.show_zebra_rows ? "on" : "off"} | Accent: {config.accent_color}
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>PDF preview</h3>
        <p className="subtle">Select a PO and open the live PDF generated with this template.</p>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <select value={previewPoId} onChange={(e) => setPreviewPoId(e.target.value)} disabled={poOptions.length === 0}>
            {poOptions.length === 0 && <option value="">No purchase orders available</option>}
            {poOptions.map((po) => (
              <option key={po.id} value={po.id}>{po.po_number} ({po.status})</option>
            ))}
          </select>
          <button type="button" onClick={openPdfPreview} disabled={!previewPoId || openingPreview}>
            {openingPreview ? "Opening..." : "Open PDF Preview"}
          </button>
          <a href="/admin/purchase-orders" className="subtle" style={{ textDecoration: "underline" }}>Go to purchase orders</a>
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button type="button" onClick={() => setConfig(defaultConfig)}>Revert unsaved changes</button>
        <button type="button" onClick={resetTemplate} disabled={resetting}>{resetting ? "Resetting..." : "Reset to Standard Default"}</button>
        <button type="button" className="primary" onClick={saveTemplate} disabled={saving}>
          {saving ? "Saving..." : "Save Template"}
        </button>
      </div>
    </div>
  );
}
