"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import Modal from "../../../_components/Modal";

type SupplierSummary = {
  id: string;
  name: string;
  email: string;
  phone: string;
  website: string;
  account_ref: string;
};

type CreatedByUser = {
  id: string;
  email: string;
  full_name: string | null;
};

type PO = {
  id: string;
  po_number: string | null;
  supplier_id: string;
  status: string;
  order_date: string | null;
  delivery_name: string;
  delivery_address: string;
  notes: string;
  subtotal_gbp: number;
  vat_gbp: number;
  total_gbp: number;
  created_by_user_id: string | null;
  supplier?: SupplierSummary | null;
  created_by?: CreatedByUser | null;
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

type Material = { id: string; name: string; type: string; supplier_id: string | null; nominal_code?: string; supplier_product_code?: string; cost_per_sheet_gbp?: number | null; cost_per_lm_gbp?: number | null };
type MaterialSize = { id: string; material_id: string; label: string; width_mm: number; height_mm: number | null; cost_per_sheet_gbp: number | null; cost_per_lm_gbp: number | null; length_m: number | null; custom_length_available?: boolean };

export default function PurchaseOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const fromMaterials = searchParams.get("from") === "materials";
  const id = params.id as string;
  const [err, setErr] = useState("");
  const [po, setPo] = useState<PO | null>(null);
  const [lines, setLines] = useState<POLine[]>([]);
  const [suppliers, setSuppliers] = useState<{ id: string; name: string }[]>([]);

  const [addLineOpen, setAddLineOpen] = useState(false);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialSearch, setMaterialSearch] = useState("");
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);
  const [sizes, setSizes] = useState<MaterialSize[]>([]);
  const [sizesLoading, setSizesLoading] = useState(false);
  const [selectedSize, setSelectedSize] = useState<MaterialSize | null>(null);
  const [lineDesc, setLineDesc] = useState("");
  const [lineSupplierCode, setLineSupplierCode] = useState("");
  const [lineQty, setLineQty] = useState(1);
  const [lineUom, setLineUom] = useState("sheet");
  const [lineUnitCost, setLineUnitCost] = useState(0);
  const [useCustomLength, setUseCustomLength] = useState(false);

  const [receiveOpen, setReceiveOpen] = useState(false);
  const [receiveQtys, setReceiveQtys] = useState<Record<string, number>>({});

  const [materialsById, setMaterialsById] = useState<Record<string, Material>>({});
  const [sizeLabelBySizeId, setSizeLabelBySizeId] = useState<Record<string, string>>({});

  const [savingPo, setSavingPo] = useState(false);
  const [editLineOpen, setEditLineOpen] = useState(false);
  const [editingLine, setEditingLine] = useState<POLine | null>(null);
  const [editLineDesc, setEditLineDesc] = useState("");
  const [editLineSupplierCode, setEditLineSupplierCode] = useState("");
  const [editLineQty, setEditLineQty] = useState(0);
  const [editLineUom, setEditLineUom] = useState("sheet");
  const [editLineUnitCost, setEditLineUnitCost] = useState(0);

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
      const data = await api<any[]>("/api/suppliers");
      setSuppliers(data ?? []);
    } catch {}
  }

  useEffect(() => {
    if (!id) return;
    loadPO();
    loadLines();
    loadSuppliers();
    api<Material[]>("/api/materials")
      .then((arr) => {
        const map: Record<string, Material> = {};
        (arr || []).forEach((m) => { map[m.id] = m; });
        setMaterialsById(map);
      })
      .catch(() => setMaterialsById({}));
  }, [id]);

  const [materialIdFromUrl, setMaterialIdFromUrl] = useState<string | null>(null);
  useEffect(() => {
    const fromSearch = searchParams.get("materialId");
    const fromWindow =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("materialId")
        : null;
    setMaterialIdFromUrl(fromSearch || fromWindow);
  }, [searchParams]);
  const materialIdOpenDoneRef = useRef<string | null>(null);
  useEffect(() => {
    if (!id || !materialIdFromUrl) return;
    if (materialIdOpenDoneRef.current === materialIdFromUrl) return;
    materialIdOpenDoneRef.current = materialIdFromUrl;
    setAddLineOpen(true);
    let cancelled = false;
    api<Material>(`/api/materials/${materialIdFromUrl}`)
      .then((m) => {
        if (cancelled || !m) return;
        setSelectedMaterial(m);
        setMaterialSearch(m.name || "");
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [id, materialIdFromUrl]);

  useEffect(() => {
    if (lines.length === 0) {
      setSizeLabelBySizeId({});
      return;
    }
    const materialIds = Array.from(new Set(lines.map((l) => l.material_id).filter(Boolean))) as string[];
    if (materialIds.length === 0) {
      setSizeLabelBySizeId({});
      return;
    }
    Promise.all(materialIds.map((mid) => api<MaterialSize[]>(`/api/materials/${mid}/sizes`)))
      .then((results) => {
        const map: Record<string, string> = {};
        results.forEach((sizes) => {
          (sizes || []).forEach((s) => { map[s.id] = s.label; });
        });
        setSizeLabelBySizeId(map);
      })
      .catch(() => setSizeLabelBySizeId({}));
  }, [lines]);

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
      setSizesLoading(false);
      return;
    }
    setSizesLoading(true);
    api<MaterialSize[]>(`/api/materials/${selectedMaterial.id}/sizes`)
      .then((arr) => {
        const sizeList = arr || [];
        setSizes(sizeList);
        const isFromMaterialsOrder = !!materialIdFromUrl && selectedMaterial?.id === materialIdFromUrl;
        if (isFromMaterialsOrder && sizeList.length === 1) {
          setSelectedSize(sizeList[0]);
        } else {
          setSelectedSize(null);
        }
      })
      .catch(() => setSizes([]))
      .finally(() => setSizesLoading(false));
  }, [selectedMaterial?.id, materialIdFromUrl]);

  useEffect(() => {
    if (!selectedMaterial) return;
    const name = selectedMaterial.name || "";
    const code = (selectedMaterial as Material & { nominal_code?: string }).nominal_code || "";
    setLineDesc(code ? `${name} (${code})` : name);
    setLineSupplierCode(selectedMaterial.supplier_product_code || "");
    if (selectedMaterial.type === "sheet" && selectedSize) {
      setLineUnitCost(selectedSize.cost_per_sheet_gbp ?? 0);
      setLineUom("sheet");
    } else if (selectedMaterial.type === "roll") {
      const costPerLm = selectedSize?.cost_per_lm_gbp ?? selectedMaterial.cost_per_lm_gbp ?? 0;
      const lengthM = selectedSize?.length_m ?? null;
      const customAllowed = !!(selectedSize as MaterialSize | null)?.custom_length_available;
      const useRolls = selectedSize && lengthM != null && lengthM > 0 && (!customAllowed || !useCustomLength);
      if (useRolls) {
        setLineUom("roll");
        setLineUnitCost(costPerLm * lengthM);
        setLineQty(1);
      } else {
        setLineUnitCost(costPerLm);
        setLineUom("lm");
        setLineQty(lengthM ?? 1);
      }
    }
  }, [selectedMaterial, selectedSize, useCustomLength]);

  useEffect(() => {
    if (selectedSize && !(selectedSize as MaterialSize).custom_length_available) {
      setUseCustomLength(false);
    }
  }, [selectedSize]);

  const supplierName = po ? (po.supplier?.name ?? suppliers.find((s) => s.id === po.supplier_id)?.name ?? po.supplier_id) : "";
  const createdByLabel = po?.created_by ? (po.created_by.full_name?.trim() || po.created_by.email) : null;
  const isDraftPoNumber = !po?.po_number || String(po.po_number).startsWith("DRAFT-");

  function openAddLine() {
    setSelectedMaterial(null);
    setSelectedSize(null);
    setMaterialSearch("");
    setLineDesc("");
    setLineSupplierCode("");
    setLineQty(1);
    setLineUom("sheet");
    setLineUnitCost(0);
    setUseCustomLength(false);
    setSizes([]);
    setAddLineOpen(true);
  }

  function isAddLineFormDirty(): boolean {
    return !!(lineDesc?.trim() || selectedMaterial || lineSupplierCode?.trim() || lineQty !== 1 || lineUnitCost !== 0);
  }

  function doCloseAddLineModal() {
    setAddLineOpen(false);
    setSelectedMaterial(null);
    setSelectedSize(null);
  }

  const addLineModalRequestCloseRef = useRef<(() => void) | null>(null);
  const editLineModalRequestCloseRef = useRef<(() => void) | null>(null);
  const receiveModalRequestCloseRef = useRef<(() => void) | null>(null);

  function isReceiveFormDirty(): boolean {
    return Object.values(receiveQtys).some((v) => v != null && v > 0);
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
      doCloseAddLineModal();
      await loadLines();
      await loadPO();
    } catch (e: any) {
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg);
      throw e;
    }
  }

  function openEditLine(line: POLine) {
    if (!line.active) return;
    setEditingLine(line);
    setEditLineDesc(line.description || "");
    setEditLineSupplierCode(line.supplier_product_code || "");
    setEditLineQty(line.qty);
    setEditLineUom(line.uom);
    setEditLineUnitCost(line.unit_cost_gbp ?? 0);
    setEditLineOpen(true);
  }

  function isEditLineFormDirty(): boolean {
    if (!editingLine) return false;
    return (
      (editLineDesc || "").trim() !== (editingLine.description || "").trim() ||
      (editLineSupplierCode || "").trim() !== (editingLine.supplier_product_code || "").trim() ||
      editLineQty !== editingLine.qty ||
      editLineUom !== (editingLine.uom || "sheet") ||
      editLineUnitCost !== (editingLine.unit_cost_gbp ?? 0)
    );
  }

  function doCloseEditLineModal() {
    setEditLineOpen(false);
    setEditingLine(null);
  }

  async function saveEditLine() {
    if (!editingLine) return;
    setErr("");
    try {
      await api(`/api/purchase-order-lines/${editingLine.id}`, {
        method: "PUT",
        body: JSON.stringify({
          description: editLineDesc.trim(),
          supplier_product_code: editLineSupplierCode.trim(),
          qty: editLineQty,
          uom: editLineUom,
          unit_cost_gbp: editLineUnitCost,
        }),
      });
      doCloseEditLineModal();
      await loadLines();
      await loadPO();
    } catch (e: any) {
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg);
      throw e;
    }
  }

  async function removeLine(line: POLine) {
    if (!line.active) return;
    if (!confirm(`Remove line "${line.description || "—"}" from this purchase order?`)) return;
    setErr("");
    try {
      await api(`/api/purchase-order-lines/${line.id}`, { method: "DELETE" });
      await loadLines();
      await loadPO();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function removeAllLines() {
    const activeCount = lines.filter((l) => l.active).length;
    if (activeCount === 0) return;
    if (!confirm(`Remove all ${activeCount} line(s) from this purchase order?`)) return;
    setErr("");
    try {
      await api(`/api/purchase-orders/${id}/lines`, { method: "DELETE" });
      await loadLines();
      await loadPO();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function savePo() {
    setErr("");
    setSavingPo(true);
    try {
      await api(`/api/purchase-orders/${id}`, {
        method: "PUT",
        body: JSON.stringify({}),
      });
      router.push(fromMaterials ? "/purchase-orders" : "/admin/purchase-orders");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSavingPo(false);
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

  async function deleteDraft() {
    if (!po?.po_number || !String(po.po_number).startsWith("DRAFT-")) return;
    if (!confirm("Delete this draft permanently? This cannot be undone.")) return;
    setErr("");
    try {
      await api(`/api/purchase-orders/${id}`, { method: "DELETE" });
      router.push(fromMaterials ? "/purchase-orders" : "/admin/purchase-orders");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  const [processingOrder, setProcessingOrder] = useState(false);
  async function processOrder() {
    if (!po?.po_number || !String(po.po_number).startsWith("DRAFT-")) return;
    setErr("");
    setProcessingOrder(true);
    try {
      await api(`/api/purchase-orders/${id}/promote`, { method: "POST" });
      await api(`/api/purchase-orders/${id}/status`, {
        method: "POST",
        body: JSON.stringify({ status: "processed" }),
      });
      router.push(fromMaterials ? "/purchase-orders" : "/admin/purchase-orders");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setProcessingOrder(false);
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
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg);
      throw e;
    }
  }

  function doCloseReceiveModal() {
    setReceiveOpen(false);
    setReceiveQtys({});
  }

  const activeLines = lines.filter((l) => l.active);

  if (!po && !err) return <div className="subtle">Loading…</div>;
  if (!po) return <div><div className="card" style={{ borderColor: "#c00" }}>{err}</div><Link href={fromMaterials ? "/purchase-orders" : "/admin/purchase-orders"}>← Back to list</Link></div>;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link
          href={fromMaterials ? "/purchase-orders" : "/admin/purchase-orders"}
          className="subtle"
          style={{ textDecoration: "underline" }}
        >
          ← Purchase orders
        </Link>
      </div>

      <div className="card" style={{ marginBottom: 16, padding: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 16, alignItems: "start" }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Supplier</div>
            <div style={{ fontSize: 14 }}>
              {po.supplier ? (
                <>
                  <div>{po.supplier.name}</div>
                  {po.supplier.email && <div className="subtle">{po.supplier.email}</div>}
                  {po.supplier.phone && <div className="subtle">{po.supplier.phone}</div>}
                  {po.supplier.website && <div className="subtle">{po.supplier.website}</div>}
                  {po.supplier.account_ref && <div className="subtle">Account ref: {po.supplier.account_ref}</div>}
                </>
              ) : (
                <div>{supplierName || po.supplier_id}</div>
              )}
            </div>
          </div>
          {createdByLabel ? (
            <div className="subtle" style={{ fontSize: 14 }}>
              Created by {createdByLabel}
            </div>
          ) : po.created_by_user_id ? (
            <div className="subtle" style={{ fontSize: 14 }}>Created by —</div>
          ) : null}
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>
            {isDraftPoNumber ? "Draft" : po.po_number}
            {!(isDraftPoNumber && po.status === "draft") && (
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
                {po.status.charAt(0).toUpperCase() + po.status.slice(1).replace(/_/g, " ")}
              </span>
            )}
          </h1>
          <div className="subtle" style={{ marginTop: 4 }}>{supplierName}</div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {isDraftPoNumber && (
            <button type="button" className="primary" onClick={savePo} disabled={savingPo}>
              {savingPo ? "Saving…" : "Save draft"}
            </button>
          )}
          <button
            type="button"
            onClick={async () => {
              try {
                const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
                const res = await fetch(`/api/purchase-orders/${id}.pdf`, {
                  headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
                if (!res.ok) throw new Error("Failed to load PDF");
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `${isDraftPoNumber ? "PO-draft" : po.po_number}.pdf`;
                a.click();
                URL.revokeObjectURL(url);
              } catch (e: any) {
                setErr(e?.message || "PDF download failed");
              }
            }}
          >
            Download PDF
          </button>
          {(po.status === "draft" || po.status === "processed") && (
            <>
              <button type="button" onClick={markSent}>Mark Sent</button>
              {isDraftPoNumber && <button type="button" className="danger" onClick={deleteDraft}>Delete draft</button>}
            </>
          )}
          <button type="button" onClick={() => { setReceiveOpen(true); setReceiveQtys({}); }}>Receive</button>
          <button type="button" onClick={() => { loadPO(); loadLines(); }}>Refresh</button>
        </div>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#c00", whiteSpace: "pre-wrap", marginBottom: 12 }}>{err}</div>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <span className="subtle" style={{ fontWeight: 600 }}>Lines</span>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" className="danger" onClick={removeAllLines} disabled={!lines.some((l) => l.active)}>
              Remove all lines
            </button>
            <button type="button" onClick={openAddLine}>Add Line</button>
          </div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "6px 8px" }}>Description</th>
                <th style={{ padding: "6px 8px" }}>Order number</th>
                <th style={{ padding: "6px 8px" }}>Supplier code (SKU)</th>
                <th style={{ padding: "6px 8px" }}>Size</th>
                <th style={{ padding: "6px 8px" }}>Qty</th>
                <th style={{ padding: "6px 8px" }}>UOM</th>
                <th style={{ padding: "6px 8px" }}>Unit cost</th>
                <th style={{ padding: "6px 8px" }}>Total</th>
                <th style={{ padding: "6px 8px" }}>Received</th>
                <th style={{ padding: "6px 8px", width: 120 }}></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.id} style={{ borderBottom: "1px solid #eee", background: l.active ? undefined : "#f5f5f5" }}>
                  <td style={{ padding: "6px 8px" }}>{l.description || "—"}{!l.active && <span className="subtle"> (removed)</span>}</td>
                  <td style={{ padding: "6px 8px" }} className="subtle">{l.material_id ? (materialsById[l.material_id]?.nominal_code ?? "—") : "—"}</td>
                  <td style={{ padding: "6px 8px" }}>{l.supplier_product_code || "—"}</td>
                  <td style={{ padding: "6px 8px" }} className="subtle">{l.material_size_id ? (sizeLabelBySizeId[l.material_size_id] ?? "—") : "—"}</td>
                  <td style={{ padding: "6px 8px" }}>{l.qty}</td>
                  <td style={{ padding: "6px 8px" }}>{l.uom}</td>
                  <td style={{ padding: "6px 8px" }}>£{l.unit_cost_gbp?.toFixed(2)}</td>
                  <td style={{ padding: "6px 8px" }}>£{l.line_total_gbp?.toFixed(2)}</td>
                  <td style={{ padding: "6px 8px" }}>{l.received_qty ?? 0}</td>
                  <td style={{ padding: "6px 8px" }}>
                    {l.active && (
                      <div style={{ display: "flex", gap: 8 }}>
                        <button type="button" onClick={() => openEditLine(l)}>Edit</button>
                        <button type="button" className="danger" onClick={() => removeLine(l)}>Remove</button>
                      </div>
                    )}
                  </td>
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
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
          {isDraftPoNumber && (
            <button type="button" className="primary" onClick={processOrder} disabled={processingOrder}>
              {processingOrder ? "Processing…" : "Process order"}
            </button>
          )}
        </div>
      </div>

      <Modal
        open={addLineOpen}
        title="Add line"
        onClose={doCloseAddLineModal}
        wide
        isDirty={addLineOpen && isAddLineFormDirty()}
        onSave={saveLine}
        requestCloseRef={addLineModalRequestCloseRef}
      >
        <div style={{ display: "grid", gap: 12 }}>
          {materialIdFromUrl && selectedMaterial ? (
            <div style={{ padding: "10px 12px", background: "#f5f5f7", borderRadius: 10, border: "1px solid #e5e5e7" }}>
              <div className="subtle" style={{ fontSize: 12, marginBottom: 4 }}>Material (from materials)</div>
              <div style={{ fontWeight: 600 }}>{selectedMaterial.name} <span className="subtle">({selectedMaterial.type})</span></div>
            </div>
          ) : (
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
          )}
          {selectedMaterial && (
            <div>
              <label className="subtle">{selectedMaterial.type === "roll" ? "Roll width" : "Size"}</label>
              {sizesLoading ? (
                <div className="subtle" style={{ marginTop: 4, fontSize: 14 }}>Loading…</div>
              ) : sizes.length === 0 ? (
                <div className="subtle" style={{ marginTop: 4, fontSize: 14 }}>{selectedMaterial.type === "sheet" ? "No sizes defined" : "No roll widths defined"}</div>
              ) : (
                <select
                  value={selectedSize?.id ?? ""}
                  onChange={(e) => setSelectedSize(sizes.find((s) => s.id === e.target.value) ?? null)}
                  style={{ width: "100%", marginTop: 4 }}
                >
                  <option value="">—</option>
                  {sizes.map((s) => (
                    <option key={s.id} value={s.id}>
                      {selectedMaterial.type === "roll"
                        ? `${s.label} (${s.width_mm} mm × ${s.length_m ?? "—"}m${s.cost_per_lm_gbp != null ? ` · £${s.cost_per_lm_gbp}/lm` : ""})`
                        : `${s.label} (${s.width_mm}×${s.height_mm ?? "—"})`}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}
          {selectedMaterial && (selectedMaterial as Material & { nominal_code?: string }).nominal_code != null && (
            <div>
              <label className="subtle">Order number / Nominal code</label>
              <input
                value={(selectedMaterial as Material & { nominal_code?: string }).nominal_code || ""}
                readOnly
                style={{ width: "100%", marginTop: 4, background: "#f5f5f5" }}
              />
            </div>
          )}
          <div>
            <label className="subtle" htmlFor="add-line-desc">Description</label>
            <input id="add-line-desc" value={lineDesc} onChange={(e) => setLineDesc(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div>
            <label className="subtle">Supplier product code (SKU)</label>
            <input value={lineSupplierCode} onChange={(e) => setLineSupplierCode(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          {(selectedMaterial?.type === "roll" && selectedSize?.length_m != null && (selectedSize as MaterialSize).custom_length_available) && (
            <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
              <input type="checkbox" checked={useCustomLength} onChange={(e) => setUseCustomLength(e.target.checked)} />
              Use custom length (lm)
            </label>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div>
              <label className="subtle">
                {selectedMaterial?.type === "roll" && selectedSize?.length_m != null && !useCustomLength
                  ? "Number of rolls"
                  : "Qty"}
              </label>
              <input
                type="number"
                step={lineUom === "roll" ? 1 : "any"}
                min={lineUom === "roll" ? 1 : undefined}
                value={lineQty}
                onChange={(e) => setLineQty(parseFloat(e.target.value) || (lineUom === "roll" ? 1 : 0))}
                style={{ width: "100%", marginTop: 4 }}
              />
            </div>
            <div>
              <label className="subtle">UOM</label>
              {selectedMaterial?.type === "roll" && selectedSize?.length_m != null && !useCustomLength ? (
                <div style={{ marginTop: 4, padding: "8px 12px", background: "#f5f5f5", borderRadius: 6 }}>
                  roll ({selectedSize.length_m}m each)
                </div>
              ) : (
                <select value={lineUom} onChange={(e) => setLineUom(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                  <option value="sheet">sheet</option>
                  <option value="lm">lm</option>
                  <option value="roll">roll</option>
                  <option value="each">each</option>
                  <option value="pack">pack</option>
                </select>
              )}
            </div>
            <div>
              <label className="subtle">Unit cost (£)</label>
              <input type="number" step="0.01" value={lineUnitCost} onChange={(e) => setLineUnitCost(parseFloat(e.target.value) || 0)} style={{ width: "100%", marginTop: 4 }} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" onClick={() => addLineModalRequestCloseRef.current?.()}>Cancel</button>
            <button type="button" className="primary" onClick={saveLine} disabled={!lineDesc.trim()}>Save line</button>
          </div>
        </div>
      </Modal>

      <Modal
        open={editLineOpen}
        title="Edit line"
        onClose={doCloseEditLineModal}
        wide
        isDirty={editLineOpen && !!editingLine && isEditLineFormDirty()}
        onSave={saveEditLine}
        requestCloseRef={editLineModalRequestCloseRef}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <div>
            <label className="subtle">Description</label>
            <input value={editLineDesc} onChange={(e) => setEditLineDesc(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div>
            <label className="subtle">Supplier product code (SKU)</label>
            <input value={editLineSupplierCode} onChange={(e) => setEditLineSupplierCode(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div>
              <label className="subtle">Qty</label>
              <input type="number" step="any" value={editLineQty} onChange={(e) => setEditLineQty(parseFloat(e.target.value) || 0)} style={{ width: "100%", marginTop: 4 }} />
            </div>
            <div>
              <label className="subtle">UOM</label>
              <select value={editLineUom} onChange={(e) => setEditLineUom(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                <option value="sheet">sheet</option>
                <option value="lm">lm</option>
                <option value="roll">roll</option>
                <option value="each">each</option>
                <option value="pack">pack</option>
              </select>
            </div>
            <div>
              <label className="subtle">Unit cost (£)</label>
              <input type="number" step="0.01" value={editLineUnitCost} onChange={(e) => setEditLineUnitCost(parseFloat(e.target.value) || 0)} style={{ width: "100%", marginTop: 4 }} />
            </div>
          </div>
          {err && editLineOpen && <div style={{ color: "#c00", fontSize: 14 }}>{err}</div>}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" onClick={() => editLineModalRequestCloseRef.current?.()}>Cancel</button>
            <button type="button" className="primary" onClick={saveEditLine} disabled={!editLineDesc.trim()}>Save changes</button>
          </div>
        </div>
      </Modal>

      <Modal
        open={receiveOpen}
        title="Receive"
        onClose={doCloseReceiveModal}
        wide
        isDirty={receiveOpen && isReceiveFormDirty()}
        onSave={submitReceive}
        requestCloseRef={receiveModalRequestCloseRef}
      >
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
            <button type="button" onClick={() => receiveModalRequestCloseRef.current?.()}>Cancel</button>
            <button type="button" className="primary" onClick={submitReceive}>Submit receive</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
