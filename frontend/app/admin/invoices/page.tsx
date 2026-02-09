"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../../../lib/api";

type SupplierInvoice = {
  id: string;
  supplier_id: string;
  invoice_number: string;
  invoice_date: string | null;
  currency: string;
  subtotal_gbp: number;
  vat_gbp: number;
  total_gbp: number;
  status: string;
  matched_po_id: string | null;
  match_confidence: number;
  match_notes: string;
  file_path: string;
  created_at?: string;
};

type Candidate = {
  po_id: string;
  po_number: string;
  po_total: number;
  total_diff: number;
  status: string;
  score: number;
  reason: string;
};

function Modal({
  open,
  title,
  children,
  onClose,
  zIndex = 9999,
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  zIndex?: number;
}) {
  if (!open) return null;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.25)",
        backdropFilter: "blur(10px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        zIndex,
      }}
      onMouseDown={onClose}
    >
      <div
        style={{
          width: "min(900px, 100%)",
          maxHeight: "90vh",
          background: "#fff",
          borderRadius: 20,
          boxShadow: "0 30px 80px rgba(0,0,0,0.2)",
          border: "1px solid #e5e5e7",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div style={{ padding: 18, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between" }}>
          <div style={{ fontWeight: 600 }}>{title}</div>
          <button onClick={onClose}>✕</button>
        </div>
        <div style={{ padding: 18, overflow: "auto", flex: 1 }}>{children}</div>
      </div>
    </div>
  );
}

function num(v: any, fallback = 0) {
  const x = typeof v === "number" ? v : parseFloat(String(v ?? ""));
  return Number.isFinite(x) ? x : fallback;
}

export default function AdminInvoicesPage() {
  const [err, setErr] = useState("");
  const [invoices, setInvoices] = useState<SupplierInvoice[]>([]);
  const [suppliers, setSuppliers] = useState<{ id: string; name: string }[]>([]);

  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [supplierFilterId, setSupplierFilterId] = useState<string>("all");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<SupplierInvoice | null>(null);

  // Upload form
  const [uploadSupplierId, setUploadSupplierId] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadInvoiceNumber, setUploadInvoiceNumber] = useState("");
  const [uploadInvoiceDate, setUploadInvoiceDate] = useState("");
  const [uploadSubtotal, setUploadSubtotal] = useState("");
  const [uploadVat, setUploadVat] = useState("");
  const [uploadTotal, setUploadTotal] = useState("");
  const [uploadCurrency, setUploadCurrency] = useState("GBP");

  // Detail: candidates
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);

  async function load() {
    setErr("");
    try {
      const [invList, supList] = await Promise.all([
        api("/api/supplier-invoices"),
        api("/api/suppliers"),
      ]);
      setInvoices(invList || []);
      setSuppliers(supList || []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (suppliers.length && !uploadSupplierId) setUploadSupplierId(suppliers[0].id);
  }, [suppliers]);

  const filtered = useMemo(() => {
    const text = q.trim().toLowerCase();
    return (invoices || [])
      .filter((inv) => {
        if (statusFilter !== "all" && inv.status !== statusFilter) return false;
        if (supplierFilterId !== "all" && inv.supplier_id !== supplierFilterId) return false;
        if (!text) return true;
        const supName = suppliers.find((s) => s.id === inv.supplier_id)?.name || "";
        return (
          (inv.invoice_number || "").toLowerCase().includes(text) ||
          (inv.id || "").toLowerCase().includes(text) ||
          supName.toLowerCase().includes(text)
        );
      })
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
  }, [invoices, q, statusFilter, supplierFilterId, suppliers]);

  function openUploadModal() {
    setUploadSupplierId(suppliers.length ? suppliers[0].id : "");
    setUploadFile(null);
    setUploadInvoiceNumber("");
    setUploadInvoiceDate("");
    setUploadSubtotal("");
    setUploadVat("");
    setUploadTotal("");
    setUploadCurrency("GBP");
    setUploadModalOpen(true);
  }

  async function submitUpload() {
    setErr("");
    if (!uploadSupplierId) {
      setErr("Select a supplier");
      return;
    }
    if (!uploadFile || !uploadFile.name.toLowerCase().endsWith(".pdf")) {
      setErr("Please select a PDF file");
      return;
    }
    try {
      const form = new FormData();
      form.append("file", uploadFile);
      form.append("supplier_id", uploadSupplierId);
      form.append("invoice_number", uploadInvoiceNumber);
      if (uploadInvoiceDate) form.append("invoice_date", uploadInvoiceDate);
      form.append("subtotal_gbp", String(num(uploadSubtotal, 0)));
      form.append("vat_gbp", String(num(uploadVat, 0)));
      form.append("total_gbp", String(num(uploadTotal, 0)));
      form.append("currency", uploadCurrency);
      const res = await api("/api/supplier-invoices/upload", {
        method: "POST",
        body: form,
      });
      setUploadModalOpen(false);
      await load();
      if (res?.id) setSelectedInvoice(res);
      setDetailModalOpen(true);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function openDetail(inv: SupplierInvoice) {
    setSelectedInvoice(inv);
    setCandidates([]);
    setDetailModalOpen(true);
  }

  async function loadCandidates() {
    if (!selectedInvoice?.id) return;
    setCandidatesLoading(true);
    setErr("");
    try {
      const res = await api(`/api/supplier-invoices/${selectedInvoice.id}/candidates`);
      setCandidates(res?.candidates || []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setCandidatesLoading(false);
    }
  }

  async function matchToPo(poId: string) {
    if (!selectedInvoice?.id) return;
    setErr("");
    try {
      const updated = await api(`/api/supplier-invoices/${selectedInvoice.id}/match`, {
        method: "POST",
        body: JSON.stringify({ po_id: poId }),
      });
      setSelectedInvoice(updated);
      await load();
      setCandidates([]);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function openPdf(invoiceId: string) {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const url = `${window.location.origin}/api/supplier-invoices/${invoiceId}.pdf`;
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        const u = URL.createObjectURL(blob);
        window.open(u, "_blank");
      })
      .catch((e) => setErr(String(e)));
  }

  function supplierName(id: string) {
    return suppliers.find((s) => s.id === id)?.name || id;
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Supplier Invoices</h1>
          <div className="subtle">Upload invoices and match them to purchase orders.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={load}>Refresh</button>
          <button className="primary" onClick={openUploadModal}>Upload Invoice</button>
        </div>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#c00", whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {err}
        </div>
      )}

      <div className="card section">
        <div className="row" style={{ alignItems: "center", flexWrap: "wrap" }}>
          <div className="col">
            <input
              placeholder="Search supplier, invoice number..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="col">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">All statuses</option>
              <option value="uploaded">Uploaded</option>
              <option value="suggested">Suggested</option>
              <option value="matched">Matched</option>
              <option value="mismatch">Mismatch</option>
              <option value="duplicate">Duplicate</option>
            </select>
          </div>
          <div className="col">
            <select value={supplierFilterId} onChange={(e) => setSupplierFilterId(e.target.value)}>
              <option value="all">All suppliers</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 10px" }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "0 10px" }}>Invoice / Supplier</th>
                <th style={{ padding: "0 10px" }}>Date</th>
                <th style={{ padding: "0 10px" }}>Total</th>
                <th style={{ padding: "0 10px" }}>Status</th>
                <th style={{ padding: "0 10px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((inv, index) => (
                <tr
                  key={inv.id}
                  style={{
                    background: hoveredId === inv.id ? "#f0f0f2" : index % 2 === 0 ? "#ffffff" : "#f8f8f8",
                    border: "1px solid #eee",
                    cursor: "pointer",
                  }}
                  onMouseEnter={() => setHoveredId(inv.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onDoubleClick={() => openDetail(inv)}
                >
                  <td style={{ padding: "12px 10px", borderTopLeftRadius: 12, borderBottomLeftRadius: 12 }}>
                    <div style={{ fontWeight: 600 }}>
                      {inv.invoice_number || inv.id}
                    </div>
                    <div className="subtle">{supplierName(inv.supplier_id)}</div>
                  </td>
                  <td style={{ padding: "12px 10px" }}>
                    {inv.invoice_date ? new Date(inv.invoice_date).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "12px 10px" }}>£{num(inv.total_gbp).toFixed(2)}</td>
                  <td style={{ padding: "12px 10px" }}>
                    <span style={{
                      padding: "2px 8px",
                      borderRadius: 999,
                      fontSize: 12,
                      background: inv.status === "matched" ? "#d1fae5" : inv.status === "mismatch" ? "#fee2e2" : inv.status === "duplicate" ? "#fef3c7" : "#e5e7eb",
                    }}>
                      {inv.status}
                    </span>
                  </td>
                  <td style={{ padding: "12px 10px", borderTopRightRadius: 12, borderBottomRightRadius: 12 }}>
                    <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }} onDoubleClick={(e) => e.stopPropagation()}>
                      <button onClick={() => openDetail(inv)}>Open</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && <div className="subtle" style={{ marginTop: 10 }}>No invoices found.</div>}
      </div>

      {/* Upload Modal */}
      <Modal open={uploadModalOpen} title="Upload Invoice" onClose={() => setUploadModalOpen(false)}>
        <div style={{ display: "grid", gap: 12 }}>
          <div className="row">
            <div className="col">
              <label className="subtle">Supplier</label>
              <select
                value={uploadSupplierId}
                onChange={(e) => setUploadSupplierId(e.target.value)}
              >
                <option value="">Select supplier</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">PDF file</label>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Invoice number</label>
              <input
                value={uploadInvoiceNumber}
                onChange={(e) => setUploadInvoiceNumber(e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="col">
              <label className="subtle">Invoice date</label>
              <input
                type="date"
                value={uploadInvoiceDate}
                onChange={(e) => setUploadInvoiceDate(e.target.value)}
              />
            </div>
            <div className="col">
              <label className="subtle">Currency</label>
              <select value={uploadCurrency} onChange={(e) => setUploadCurrency(e.target.value)}>
                <option value="GBP">GBP</option>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Subtotal (£)</label>
              <input
                type="number"
                step="0.01"
                value={uploadSubtotal}
                onChange={(e) => setUploadSubtotal(e.target.value)}
              />
            </div>
            <div className="col">
              <label className="subtle">VAT (£)</label>
              <input
                type="number"
                step="0.01"
                value={uploadVat}
                onChange={(e) => setUploadVat(e.target.value)}
              />
            </div>
            <div className="col">
              <label className="subtle">Total (£)</label>
              <input
                type="number"
                step="0.01"
                value={uploadTotal}
                onChange={(e) => setUploadTotal(e.target.value)}
              />
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
            <button onClick={() => setUploadModalOpen(false)}>Cancel</button>
            <button className="primary" onClick={submitUpload} disabled={!uploadFile || !uploadSupplierId}>
              Upload
            </button>
          </div>
        </div>
      </Modal>

      {/* Detail Modal */}
      <Modal
        open={detailModalOpen}
        title={selectedInvoice ? `Invoice ${selectedInvoice.invoice_number || selectedInvoice.id}` : "Invoice"}
        onClose={() => { setDetailModalOpen(false); setSelectedInvoice(null); setCandidates([]); }}
        zIndex={10000}
      >
        {selectedInvoice && (
          <div style={{ display: "grid", gap: 16 }}>
            {selectedInvoice.status === "mismatch" && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(239, 68, 68, 0.12)",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  color: "#b91c1c",
                  fontSize: 14,
                }}
              >
                Totals differ from matched PO. {selectedInvoice.match_notes}
              </div>
            )}
            {selectedInvoice.status === "duplicate" && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(245, 158, 11, 0.12)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  color: "#b45309",
                  fontSize: 14,
                }}
              >
                {selectedInvoice.match_notes || "Possible duplicate invoice number for this supplier."}
              </div>
            )}

            <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
              <div className="subtle" style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Captured fields</div>
              <div className="row">
                <div className="col">
                  <span className="subtle">Supplier</span>
                  <div>{supplierName(selectedInvoice.supplier_id)}</div>
                </div>
                <div className="col">
                  <span className="subtle">Invoice number</span>
                  <div>{selectedInvoice.invoice_number || "—"}</div>
                </div>
                <div className="col">
                  <span className="subtle">Date</span>
                  <div>{selectedInvoice.invoice_date ? new Date(selectedInvoice.invoice_date).toLocaleDateString() : "—"}</div>
                </div>
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <div className="col">
                  <span className="subtle">Subtotal</span>
                  <div>£{num(selectedInvoice.subtotal_gbp).toFixed(2)}</div>
                </div>
                <div className="col">
                  <span className="subtle">VAT</span>
                  <div>£{num(selectedInvoice.vat_gbp).toFixed(2)}</div>
                </div>
                <div className="col">
                  <span className="subtle">Total</span>
                  <div>£{num(selectedInvoice.total_gbp).toFixed(2)}</div>
                </div>
              </div>
            </div>

            {selectedInvoice.file_path && (
              <div>
                <button className="primary" onClick={() => openPdf(selectedInvoice.id)}>
                  Open PDF
                </button>
              </div>
            )}

            <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
              <div className="subtle" style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Match to PO</div>
              <button onClick={loadCandidates} disabled={candidatesLoading} style={{ marginBottom: 12 }}>
                {candidatesLoading ? "Loading…" : "Find matches"}
              </button>
              {candidates.length > 0 && (
                <div style={{ display: "grid", gap: 8 }}>
                  {candidates.map((c) => (
                    <div
                      key={c.po_id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: 10,
                        background: "#fff",
                        border: "1px solid #eee",
                        borderRadius: 10,
                      }}
                    >
                      <div>
                        <div><strong>{c.po_number}</strong> · £{c.po_total.toFixed(2)} · diff £{c.total_diff.toFixed(2)} · {c.status}</div>
                        <div className="subtle">{c.reason}</div>
                      </div>
                      <button className="primary" onClick={() => matchToPo(c.po_id)}>
                        Match to this PO
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {selectedInvoice.matched_po_id && (
                <div className="subtle" style={{ marginTop: 8 }}>
                  Matched to PO: {selectedInvoice.matched_po_id}
                </div>
              )}
            </div>

            {err && detailModalOpen && (
              <div style={{ color: "#c00", fontSize: 14, whiteSpace: "pre-wrap" }}>{err}</div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
