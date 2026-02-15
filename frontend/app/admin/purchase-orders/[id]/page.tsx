"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import Modal from "../../../_components/Modal";

type PO = {
  id: string;
  po_number: string;
  supplier_id: string;
  status: string;
  order_date: string | null;
  delivery_name: string;
  delivery_address: string;
  notes: string;
  internal_notes: string;
  subtotal_gbp: number;
  vat_gbp: number;
  total_gbp: number;
};

type POLine = {
  id: string;
  po_id: string;
  material_id: string | null;
  material_size_id: string | null;
  description: string;
  supplier_product_code: string;
  qty: number;
  uom: string;
  unit_cost_gbp: number;
  line_total_gbp: number;
  received_qty: number;
  active: boolean;
};

type Material = { id: string; name: string; type: string; supplier_id: string | null; supplier_product_code?: string; cost_per_sheet_gbp?: number | null; cost_per_lm_gbp?: number | null };
type MaterialSize = { id: string; material_id: string; label: string; width_mm: number; height_mm: number; cost_per_sheet_gbp: number | null };
type Supplier = { id: string; name: string; email: string };

export default function PurchaseOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [err, setErr] = useState("");
  const [notice, setNotice] = useState("");
  const [po, setPo] = useState<PO | null>(null);
  const [lines, setLines] = useState<POLine[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);

  const [deliveryName, setDeliveryName] = useState("");
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [poNotes, setPoNotes] = useState("");
  const [internalNotes, setInternalNotes] = useState("");
  const [savingPO, setSavingPO] = useState(false);
  const [outputOpen, setOutputOpen] = useState(false);
  const [emailTo, setEmailTo] = useState("");
  const [emailingPO, setEmailingPO] = useState(false);

  const [addLineOpen, setAddLineOpen] = useState(false);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialSearch, setMaterialSearch] = useState("");
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);
  const [sizes, setSizes] = useState<MaterialSize[]>([]);
  const [selectedSize, setSelectedSize] = useState<MaterialSize | null>(null);
  const [lineDesc, setLineDesc] = useState("");
  const [lineSupplierCode, setLineSupplierCode] = useState("");
  const [lineQty, setLineQty] = useState(1);
  const [lineUom, setLineUom] = useState("sheet");
  const [lineUnitCost, setLineUnitCost] = useState(0);

  const [receiveOpen, setReceiveOpen] = useState(false);
  const [receiveQtys, setReceiveQtys] = useState<Record<string, number>>({});

  async function loadPO() {
    setErr("");
    try {
      const data = await api<PO>(`/api/purchase-orders/${id}`);
      setPo(data);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      setPo(null);
    }
  }

  async function loadLines() {
    try {
      const data = await api<POLine[]>(`/api/purchase-orders/${id}/lines`);
      setLines(data ?? []);
    } catch {
      setLines([]);
    }
  }

  async function loadSuppliers() {
    try {
      const data = await api<Supplier[]>("/api/suppliers");
      setSuppliers(data ?? []);
    } catch {}
  }

  useEffect(() => {
    if (!id) return;
    loadPO();
    loadLines();
    loadSuppliers();
  }, [id]);

  useEffect(() => {
    if (!po) return;
    setDeliveryName(po.delivery_name || "");
    setDeliveryAddress(po.delivery_address || "");
    setPoNotes(po.notes || "");
    setInternalNotes(po.internal_notes || "");
  }, [po?.id, po?.delivery_name, po?.delivery_address, po?.notes, po?.internal_notes]);

  useEffect(() => {
    if (!materialSearch.trim()) {
      setMaterials([]);
      return;
    }
    let cancelled = false;
    api<Material[]>("/api/materials")
      .then((arr) => {
        if (cancelled) return;
        const q = materialSearch.trim().toLowerCase();
        setMaterials(
          (arr || []).filter(
            (m) =>
              (m.name || "").toLowerCase().includes(q) ||
              (m.id || "").toLowerCase().includes(q)
          )
        );
      })
      .catch(() => { if (!cancelled) setMaterials([]); });
    return () => { cancelled = true; };
  }, [materialSearch]);

  useEffect(() => {
    if (!selectedMaterial?.id) {
      setSizes([]);
      setSelectedSize(null);
      return;
    }
    api<MaterialSize[]>(`/api/materials/${selectedMaterial.id}/sizes`)
      .then((arr) => {
        setSizes(arr || []);
        setSelectedSize(null);
      })
      .catch(() => setSizes([]));
  }, [selectedMaterial?.id]);

  useEffect(() => {
    if (!selectedMaterial) return;
    setLineDesc(selectedMaterial.name);
    setLineSupplierCode(selectedMaterial.supplier_product_code || "");
    if (selectedMaterial.type === "sheet" && selectedSize) {
      setLineUnitCost(selectedSize.cost_per_sheet_gbp ?? 0);
      setLineUom("sheet");
    } else if (selectedMaterial.type === "roll") {
      setLineUnitCost(selectedMaterial.cost_per_lm_gbp ?? 0);
      setLineUom("lm");
    }
  }, [selectedMaterial, selectedSize]);

  const supplier = po ? suppliers.find((s) => s.id === po.supplier_id) : null;
  const supplierName = po ? (supplier?.name ?? po.supplier_id) : "";

  useEffect(() => {
    if (!supplier?.email) return;
    setEmailTo((prev) => prev || supplier.email);
  }, [supplier?.email]);

  function openAddLine() {
    setSelectedMaterial(null);
    setSelectedSize(null);
    setMaterialSearch("");
    setLineDesc("");
    setLineSupplierCode("");
    setLineQty(1);
    setLineUom("sheet");
    setLineUnitCost(0);
    setSizes([]);
    setAddLineOpen(true);
  }

  async function saveLine() {
    setErr("");
    try {
      await api(`/api/purchase-orders/${id}/lines`, {
        method: "POST",
        body: JSON.stringify({
          po_id: id,
          material_id: selectedMaterial?.id ?? null,
          material_size_id: selectedSize?.id ?? null,
          description: lineDesc.trim(),
          supplier_product_code: lineSupplierCode.trim(),
          qty: lineQty,
          uom: lineUom,
          unit_cost_gbp: lineUnitCost,
          sort_order: lines.length,
        }),
      });
      setAddLineOpen(false);
      await loadLines();
      await loadPO();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function fetchPOPdfBlob() {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const res = await fetch(`/api/purchase-orders/${id}.pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Failed to load PDF");
    return await res.blob();
  }

  async function downloadPOPdf() {
    try {
      setErr("");
      const blob = await fetchPOPdfBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${po?.po_number || "purchase-order"}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setErr(e?.message || "PDF download failed");
    }
  }

  async function printPOPdf() {
    setErr("");
    const popup = window.open("", "_blank");
    if (!popup) {
      setErr("Pop-up blocked. Allow pop-ups and try again.");
      return;
    }
    popup.document.write("<p style='font-family:sans-serif;padding:12px'>Preparing purchase order PDF…</p>");
    try {
      const blob = await fetchPOPdfBlob();
      const url = URL.createObjectURL(blob);
      popup.location.href = url;
      popup.onload = () => {
        popup.focus();
        popup.print();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
      };
    } catch (e: any) {
      popup.close();
      setErr(e?.message || "PO print failed");
    }
  }

  async function savePO(openOutput = true) {
    setErr("");
    setNotice("");
    setSavingPO(true);
    try {
      const updated = await api<PO>(`/api/purchase-orders/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          delivery_name: deliveryName.trim(),
          delivery_address: deliveryAddress.trim(),
          notes: poNotes.trim(),
          internal_notes: internalNotes.trim(),
        }),
      });
      setPo(updated);
      setNotice("Purchase order saved.");
      if (openOutput) setOutputOpen(true);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSavingPO(false);
    }
  }

  async function emailPO() {
    const to = emailTo.trim();
    if (!to) {
      setErr("Enter an email address before sending.");
      return;
    }
    setErr("");
    setNotice("");
    setEmailingPO(true);
    try {
      await api(`/api/purchase-orders/${id}/email`, {
        method: "POST",
        body: JSON.stringify({ to_email: to }),
      });
      setNotice(`Purchase order emailed to ${to}.`);
      setOutputOpen(false);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setEmailingPO(false);
    }
  }

  async function markSent() {
    setErr("");
    try {
      await api(`/api/purchase-orders/${id}/status`, {
        method: "POST",
        body: JSON.stringify({ status: "sent" }),
      });
      await loadPO();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function submitReceive() {
    setErr("");
    const payload = {
      lines: Object.entries(receiveQtys)
        .filter(([, v]) => v > 0)
        .map(([line_id, receive_qty]) => ({ line_id, receive_qty })),
    };
    if (payload.lines.length === 0) {
      setErr("Enter at least one quantity to receive");
      return;
    }
    try {
      await api(`/api/purchase-orders/${id}/receive`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setReceiveOpen(false);
      setReceiveQtys({});
      await loadPO();
      await loadLines();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  const activeLines = lines.filter((l) => l.active);

  if (!po && !err) return <div className="subtle">Loading…</div>;
  if (!po) return <div><div className="card" style={{ borderColor: "#c00" }}>{err}</div><Link href="/admin/purchase-orders">← Back to list</Link></div>;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link href="/admin/purchase-orders" className="subtle" style={{ textDecoration: "underline" }}>← Purchase orders</Link>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>
            {po.po_number}
            <span
              style={{
                marginLeft: 12,
                padding: "4px 12px",
                borderRadius: 999,
                fontSize: 14,
                fontWeight: 500,
                background: po.status === "draft" ? "#f0f0f2" : po.status === "received" ? "#d1fae5" : "#fef3c7",
                color: "#1d1d1f",
              }}
            >
              {po.status}
            </span>
          </h1>
          <div className="subtle" style={{ marginTop: 4 }}>{supplierName}</div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button type="button" className="primary" onClick={() => savePO(true)} disabled={savingPO}>
            {savingPO ? "Saving…" : "Save PO"}
          </button>
          <button
            type="button"
            onClick={downloadPOPdf}
          >
            Download PDF
          </button>
          {po.status === "draft" && (
            <button type="button" onClick={markSent}>Mark Sent</button>
          )}
          <button type="button" onClick={() => { setReceiveOpen(true); setReceiveQtys({}); }}>Receive</button>
          <button type="button" onClick={() => { loadPO(); loadLines(); }}>Refresh</button>
        </div>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#c00", whiteSpace: "pre-wrap", marginBottom: 12 }}>{err}</div>
      )}
      {notice && (
        <div className="card" style={{ borderColor: "#86efac", background: "#f0fdf4", whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {notice}
        </div>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <span className="subtle" style={{ fontWeight: 600 }}>PO details</span>
        </div>
        <div className="row" style={{ marginBottom: 10 }}>
          <div className="col">
            <label className="subtle">Supplier</label>
            <input value={supplierName} disabled style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div className="col">
            <label className="subtle">Supplier email</label>
            <input value={supplier?.email || "—"} disabled style={{ width: "100%", marginTop: 4 }} />
          </div>
        </div>
        <div className="row" style={{ marginBottom: 10 }}>
          <div className="col">
            <label className="subtle">Delivery name</label>
            <input value={deliveryName} onChange={(e) => setDeliveryName(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div className="col">
            <label className="subtle">Delivery address</label>
            <textarea rows={3} value={deliveryAddress} onChange={(e) => setDeliveryAddress(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
        </div>
        <div className="row">
          <div className="col">
            <label className="subtle">Notes (shown to supplier)</label>
            <textarea rows={3} value={poNotes} onChange={(e) => setPoNotes(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div className="col">
            <label className="subtle">Internal notes</label>
            <textarea rows={3} value={internalNotes} onChange={(e) => setInternalNotes(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <span className="subtle" style={{ fontWeight: 600 }}>Lines</span>
          <button type="button" onClick={openAddLine}>Add Line</button>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "6px 8px" }}>Description</th>
                <th style={{ padding: "6px 8px" }}>Supplier code</th>
                <th style={{ padding: "6px 8px" }}>Qty</th>
                <th style={{ padding: "6px 8px" }}>UOM</th>
                <th style={{ padding: "6px 8px" }}>Unit cost</th>
                <th style={{ padding: "6px 8px" }}>Total</th>
                <th style={{ padding: "6px 8px" }}>Received</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.id} style={{ borderBottom: "1px solid #eee", background: l.active ? undefined : "#f5f5f5" }}>
                  <td style={{ padding: "6px 8px" }}>{l.description || "—"}{!l.active && <span className="subtle"> (removed)</span>}</td>
                  <td style={{ padding: "6px 8px" }}>{l.supplier_product_code || "—"}</td>
                  <td style={{ padding: "6px 8px" }}>{l.qty}</td>
                  <td style={{ padding: "6px 8px" }}>{l.uom}</td>
                  <td style={{ padding: "6px 8px" }}>£{l.unit_cost_gbp?.toFixed(2)}</td>
                  <td style={{ padding: "6px 8px" }}>£{l.line_total_gbp?.toFixed(2)}</td>
                  <td style={{ padding: "6px 8px" }}>{l.received_qty ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {lines.length === 0 && <div className="subtle" style={{ marginTop: 8 }}>No lines. Add a line to build the PO.</div>}
      </div>

      <div className="card">
        <div style={{ display: "flex", gap: 24 }}>
          <div><span className="subtle">Subtotal</span> £{po.subtotal_gbp?.toFixed(2)}</div>
          <div><span className="subtle">VAT</span> £{po.vat_gbp?.toFixed(2)}</div>
          <div><strong>Total</strong> £{po.total_gbp?.toFixed(2)}</div>
        </div>
      </div>

      <Modal open={outputOpen} title={`Output ${po.po_number}`} onClose={() => setOutputOpen(false)}>
        <div style={{ display: "grid", gap: 12 }}>
          <p className="subtle" style={{ margin: 0 }}>
            Purchase order saved. Choose how you want to send this order.
          </p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button type="button" onClick={printPOPdf}>Print PO</button>
            <button type="button" onClick={downloadPOPdf}>Download PDF</button>
          </div>
          <div>
            <label className="subtle">Email to</label>
            <input
              value={emailTo}
              onChange={(e) => setEmailTo(e.target.value)}
              placeholder="supplier@example.com"
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" onClick={() => setOutputOpen(false)}>Close</button>
            <button type="button" className="primary" onClick={emailPO} disabled={emailingPO || !emailTo.trim()}>
              {emailingPO ? "Sending…" : "Email PO"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={addLineOpen} title="Add line" onClose={() => setAddLineOpen(false)} wide>
        <div style={{ display: "grid", gap: 12 }}>
          <div>
            <label className="subtle">Material (search)</label>
            <input
              value={materialSearch}
              onChange={(e) => setMaterialSearch(e.target.value)}
              placeholder="Type to search materials..."
              style={{ width: "100%", marginTop: 4 }}
            />
            {materials.length > 0 && (
              <ul style={{ margin: "4px 0 0", padding: "8px 0 0", listStyle: "none", borderTop: "1px solid #eee" }}>
                {materials.slice(0, 8).map((m) => (
                  <li key={m.id}>
                    <button
                      type="button"
                      style={{ background: selectedMaterial?.id === m.id ? "#e5e5e7" : "transparent", border: "none", padding: "6px 0", cursor: "pointer", width: "100%", textAlign: "left" }}
                      onClick={() => setSelectedMaterial(m)}
                    >
                      {m.name} <span className="subtle">({m.type})</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {selectedMaterial && sizes.length > 0 && (
            <div>
              <label className="subtle">Size</label>
              <select
                value={selectedSize?.id ?? ""}
                onChange={(e) => setSelectedSize(sizes.find((s) => s.id === e.target.value) ?? null)}
                style={{ width: "100%", marginTop: 4 }}
              >
                <option value="">—</option>
                {sizes.map((s) => (
                  <option key={s.id} value={s.id}>{s.label} ({s.width_mm}×{s.height_mm})</option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="subtle">Description</label>
            <input value={lineDesc} onChange={(e) => setLineDesc(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div>
            <label className="subtle">Supplier product code</label>
            <input value={lineSupplierCode} onChange={(e) => setLineSupplierCode(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div>
              <label className="subtle">Qty</label>
              <input type="number" step="any" value={lineQty} onChange={(e) => setLineQty(parseFloat(e.target.value) || 0)} style={{ width: "100%", marginTop: 4 }} />
            </div>
            <div>
              <label className="subtle">UOM</label>
              <select value={lineUom} onChange={(e) => setLineUom(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                <option value="sheet">sheet</option>
                <option value="lm">lm</option>
                <option value="roll">roll</option>
                <option value="each">each</option>
                <option value="pack">pack</option>
              </select>
            </div>
            <div>
              <label className="subtle">Unit cost (£)</label>
              <input type="number" step="0.01" value={lineUnitCost} onChange={(e) => setLineUnitCost(parseFloat(e.target.value) || 0)} style={{ width: "100%", marginTop: 4 }} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" onClick={() => setAddLineOpen(false)}>Cancel</button>
            <button type="button" className="primary" onClick={saveLine} disabled={!lineDesc.trim()}>Save line</button>
          </div>
        </div>
      </Modal>

      <Modal open={receiveOpen} title="Receive" onClose={() => setReceiveOpen(false)} wide>
        <div style={{ display: "grid", gap: 12 }}>
          <p className="subtle">Enter quantity received now for each line.</p>
          {activeLines.map((l) => (
            <div key={l.id} style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <span style={{ flex: "1 1 200px" }}>{l.description || "—"}</span>
              <span className="subtle">Ordered: {l.qty} {l.uom}</span>
              <span className="subtle">Received so far: {l.received_qty ?? 0}</span>
              <input
                type="number"
                step="any"
                min={0}
                placeholder="Receive now"
                value={receiveQtys[l.id] ?? ""}
                onChange={(e) => setReceiveQtys((prev) => ({ ...prev, [l.id]: parseFloat(e.target.value) || 0 }))}
                style={{ width: 100 }}
              />
            </div>
          ))}
          {activeLines.length === 0 && <div className="subtle">No active lines.</div>}
          {err && receiveOpen && <div style={{ color: "#c00" }}>{err}</div>}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" onClick={() => setReceiveOpen(false)}>Cancel</button>
            <button type="button" className="primary" onClick={submitReceive}>Submit receive</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
