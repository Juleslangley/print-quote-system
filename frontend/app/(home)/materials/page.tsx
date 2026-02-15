"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import Modal from "../../_components/Modal";

type Material = any;

type MaterialSize = {
  id: string;
  material_id: string;
  label: string;
  width_mm: number;
  height_mm: number;
  cost_per_sheet_gbp: number | null;
  active: boolean;
  sort_order: number;
};

function num(v: any, fallback = 0) {
  const x = typeof v === "number" ? v : parseFloat(String(v ?? ""));
  return Number.isFinite(x) ? x : fallback;
}

type CutterToolOption = { key: string; name: string };
type CutterToolEntry = { key: string; default: boolean };

export default function MaterialsPage() {
  const router = useRouter();
  const [err, setErr] = useState("");
  const [materials, setMaterials] = useState<Material[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [machines, setMachines] = useState<any[]>([]);
  const [usageByMaterial, setUsageByMaterial] = useState<Record<string, any>>({});

  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [activeOnly, setActiveOnly] = useState(false);
  const [supplierFilterId, setSupplierFilterId] = useState<string>("all");
  const [hoveredMaterialId, setHoveredMaterialId] = useState<string | null>(null);
  const [orderingMaterialId, setOrderingMaterialId] = useState<string | null>(null);
  const [navigateToPoUrl, setNavigateToPoUrl] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Material | null>(null);

  const [name, setName] = useState("");
  const [nominalCode, setNominalCode] = useState("");
  const [supplierProductCode, setSupplierProductCode] = useState("");
  const [matType, setMatType] = useState<"sheet" | "roll">("sheet");
  const [supplierId, setSupplierId] = useState<string>("");
  const [supplierStr, setSupplierStr] = useState("");
  const [wastePct, setWastePct] = useState(0.05);
  const [active, setActive] = useState(true);
  const [rollW, setRollW] = useState(0);
  const [costLm, setCostLm] = useState(0);
  const [minLm, setMinLm] = useState(1);
  const [meta, setMeta] = useState<Record<string, any>>({});
  const [cutterTools, setCutterTools] = useState<CutterToolEntry[]>([]);
  const [editAdvancedMeta, setEditAdvancedMeta] = useState(false);
  const [editMetaJson, setEditMetaJson] = useState("{}");

  const [sizes, setSizes] = useState<MaterialSize[]>([]);
  const [sizesLoading, setSizesLoading] = useState(false);
  const [sizeModalOpen, setSizeModalOpen] = useState(false);
  const [editingSize, setEditingSize] = useState<MaterialSize | null>(null);
  const [sizeLabel, setSizeLabel] = useState("");
  const [sizeWidthMm, setSizeWidthMm] = useState(0);
  const [sizeHeightMm, setSizeHeightMm] = useState(0);
  const [sizeCostPerSheet, setSizeCostPerSheet] = useState<number | "">("");
  const [sizeActive, setSizeActive] = useState(true);
  const [sizeSortOrder, setSizeSortOrder] = useState(0);

  async function load() {
    setErr("");
    try {
      const [mats, sups, machs] = await Promise.all([
        api<any[]>("/api/materials"),
        api<any[]>("/api/suppliers"),
        api<any[]>("/api/machines"),
      ]);
      setMaterials(mats ?? []);
      setSuppliers(sups ?? []);
      setMachines(machs ?? []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  const cutterToolsOptions: CutterToolOption[] = useMemo(() => {
    const cutter = machines.find((m) => m.category === "cutter" && m.active);
    const raw = (cutter?.meta as any)?.tools;
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((t: any) => t && typeof t === "object" && "key" in t)
      .map((t: any) => ({ key: String(t.key), name: String(t.name ?? t.key) }));
  }, [machines]);

  async function loadUsage(materialId: string) {
    if (usageByMaterial[materialId]) return;
    try {
      const u = await api<any>(`/api/materials/${materialId}/usage`);
      setUsageByMaterial((prev) => ({ ...prev, [materialId]: u }));
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function loadSizes(materialId: string) {
    setSizesLoading(true);
    try {
      const list = await api<any[]>(`/api/materials/${materialId}/sizes`);
      setSizes(list ?? []);
    } catch {
      setSizes([]);
    } finally {
      setSizesLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (navigateToPoUrl) {
      window.location.href = navigateToPoUrl;
      setNavigateToPoUrl(null);
    }
  }, [navigateToPoUrl]);

  useEffect(() => {
    const hash = window.location.hash?.replace("#", "");
    if (!hash) return;
    const found = materials.find((m) => m.id === hash);
    if (found) openEdit(found);
  }, [materials]);

  const filtered = useMemo(() => {
    const text = q.trim().toLowerCase();
    return (materials || [])
      .filter((m) => {
        if (typeFilter !== "all" && m.type !== typeFilter) return false;
        if (activeOnly && !m.active) return false;
        if (supplierFilterId !== "all") {
          if (supplierFilterId === "none") {
            if (m.supplier_id) return false;
          } else {
            if (m.supplier_id !== supplierFilterId) return false;
          }
        }
        if (!text) return true;
        const supName = suppliers.find((s) => s.id === m.supplier_id)?.name || m.supplier || "";
        return (
          (m.name || "").toLowerCase().includes(text) ||
          (supName || "").toLowerCase().includes(text) ||
          (m.type || "").toLowerCase().includes(text)
        );
      })
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }, [materials, q, typeFilter, activeOnly, supplierFilterId, suppliers]);

  function resetForm() {
    setName("");
    setNominalCode("");
    setSupplierProductCode("");
    setMatType("sheet");
    setSupplierId(suppliers.length ? suppliers[0].id : "");
    setSupplierStr(suppliers.length ? suppliers[0].name : "");
    setWastePct(0.05);
    setActive(true);
    setRollW(1600);
    setCostLm(0);
    setMinLm(1);
    setMeta({});
    setCutterTools([]);
    setEditAdvancedMeta(false);
    setEditMetaJson("{}");
  }

  function openCreate() {
    setEditing(null);
    setSupplierId(suppliers.length ? suppliers[0].id : "");
    setSupplierStr(suppliers.length ? suppliers[0].name : "");
    resetForm();
    setModalOpen(true);
  }

  function openEdit(m: Material) {
    setEditing(m);
    setName(m.name || "");
    setNominalCode(m.nominal_code ?? "");
    setSupplierProductCode(m.supplier_product_code ?? "");
    setMatType((m.type === "roll" ? "roll" : "sheet") as "sheet" | "roll");
    const sup = suppliers.find((s) => s.id === m.supplier_id);
    setSupplierId(m.supplier_id || "");
    setSupplierStr(sup ? sup.name : m.supplier || "");
    setWastePct(num(m.waste_pct_default, 0.05));
    setActive(!!m.active);
    setRollW(num(m.roll_width_mm, 0));
    setCostLm(num(m.cost_per_lm_gbp, 0));
    setMinLm(num(m.min_billable_lm, 1));
    setMeta(m.meta && typeof m.meta === "object" ? { ...m.meta } : {});
    const rawMeta = m.meta && typeof m.meta === "object" ? (m.meta as any) : {};
    const rawTools = rawMeta.cutter_tools;
    if (Array.isArray(rawTools) && rawTools.length > 0) {
      setCutterTools(
        rawTools
          .filter((t: any) => t && typeof t === "object" && typeof t.key === "string")
          .map((t: any) => ({ key: String(t.key), default: !!t.default }))
      );
    } else {
      const legacyKey = rawMeta.cutter_tool_key;
      if (legacyKey && typeof legacyKey === "string") {
        setCutterTools([{ key: String(legacyKey), default: true }]);
      } else {
        setCutterTools([]);
      }
    }
    setEditAdvancedMeta(false);
    setEditMetaJson(JSON.stringify(m.meta || {}, null, 2));
    setModalOpen(true);
    if (m.id) {
      loadUsage(m.id);
      loadSizes(m.id);
    }
  }

  function closeModal() {
    setModalOpen(false);
    setEditing(null);
    setSizeModalOpen(false);
    setEditingSize(null);
  }

  function openAddSize() {
    setEditingSize(null);
    setSizeLabel("");
    setSizeWidthMm(0);
    setSizeHeightMm(0);
    setSizeCostPerSheet("");
    setSizeActive(true);
    setSizeSortOrder(sizes.length);
    setSizeModalOpen(true);
  }

  function openEditSize(s: MaterialSize) {
    setEditingSize(s);
    setSizeLabel(s.label || "");
    setSizeWidthMm(num(s.width_mm, 0));
    setSizeHeightMm(num(s.height_mm, 0));
    setSizeCostPerSheet(s.cost_per_sheet_gbp != null ? s.cost_per_sheet_gbp : "");
    setSizeActive(!!s.active);
    setSizeSortOrder(s.sort_order ?? 0);
    setSizeModalOpen(true);
  }

  async function saveSize() {
    if (!editing?.id) return;
    setErr("");
    try {
      const cost = sizeCostPerSheet === "" ? null : num(sizeCostPerSheet, 0);
      if (editingSize) {
        await api(`/api/material-sizes/${editingSize.id}`, {
          method: "PUT",
          body: JSON.stringify({
            label: sizeLabel.trim(),
            width_mm: sizeWidthMm,
            height_mm: sizeHeightMm,
            cost_per_sheet_gbp: cost,
            active: sizeActive,
            sort_order: sizeSortOrder,
          }),
        });
      } else {
        await api("/api/material-sizes", {
          method: "POST",
          body: JSON.stringify({
            material_id: editing.id,
            label: sizeLabel.trim(),
            width_mm: sizeWidthMm,
            height_mm: sizeHeightMm,
            cost_per_sheet_gbp: cost,
            active: sizeActive,
            sort_order: sizeSortOrder,
          }),
        });
      }
      setSizeModalOpen(false);
      setEditingSize(null);
      await loadSizes(editing.id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function deleteSizeInModal() {
    if (!editingSize?.id) return;
    if (!confirm(`Delete size "${editingSize.label}"?`)) return;
    setErr("");
    try {
      await api(`/api/material-sizes/${editingSize.id}`, { method: "DELETE" });
      setSizeModalOpen(false);
      setEditingSize(null);
      if (editing?.id) await loadSizes(editing.id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function deleteSizeRow(s: MaterialSize) {
    if (!editing?.id) return;
    if (!confirm(`Delete size "${s.label}"?`)) return;
    setErr("");
    try {
      await api(`/api/material-sizes/${s.id}`, { method: "DELETE" });
      await loadSizes(editing.id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function saveMaterial() {
    setErr("");
    try {
      let metaToSend: Record<string, any>;
      if (editing && editAdvancedMeta) {
        try {
          const parsed = JSON.parse(editMetaJson || "{}");
          if (parsed !== null && (typeof parsed !== "object" || Array.isArray(parsed))) {
            setErr("Meta must be a JSON object");
            return;
          }
          metaToSend = { ...(parsed ?? {}) };
        } catch {
          setErr("Meta JSON invalid");
          return;
        }
      } else {
        metaToSend = { ...meta };
      }
      metaToSend.cutter_tools = cutterTools.map((t) => ({ key: t.key, default: t.default }));
      const defaultEntry = cutterTools.find((t) => t.default);
      if (defaultEntry) metaToSend.cutter_tool_key = defaultEntry.key;
      else delete metaToSend.cutter_tool_key;
      if (metaToSend.cutter_tools.length === 0) delete metaToSend.cutter_tools;
      const payload: any = {
        name: name.trim(),
        nominal_code: nominalCode.trim(),
        supplier_product_code: supplierProductCode.trim(),
        type: matType,
        supplier_id: supplierId || null,
        supplier: supplierStr || "",
        active,
        waste_pct_default: wastePct,
        meta: metaToSend,
      };
      if (matType === "sheet") {
        payload.cost_per_sheet_gbp = null;
        payload.sheet_width_mm = null;
        payload.sheet_height_mm = null;
        payload.cost_per_lm_gbp = null;
        payload.roll_width_mm = null;
        payload.min_billable_lm = null;
      } else {
        payload.roll_width_mm = rollW;
        payload.cost_per_lm_gbp = costLm;
        payload.min_billable_lm = minLm;
        payload.cost_per_sheet_gbp = null;
        payload.sheet_width_mm = null;
        payload.sheet_height_mm = null;
      }
      if (editing) {
        await api(`/api/materials/${editing.id}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await api("/api/materials", { method: "POST", body: JSON.stringify(payload) });
      }
      closeModal();
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function toggleActiveInModal(): Promise<boolean> {
    if (!editing) return false;
    setErr("");
    try {
      await api(`/api/materials/${editing.id}`, { method: "PUT", body: JSON.stringify({ active: !editing.active }) });
      await load();
      return true;
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      return false;
    }
  }

  async function deleteMaterialInModal(): Promise<boolean> {
    if (!editing) return false;
    const usage = usageByMaterial[editing.id];
    const defaultCount = (usage?.default_in_templates?.length ?? 0) + (usage?.allowed_in_templates?.length ?? 0);
    if (defaultCount > 0) {
      setErr("Cannot delete: material is used in templates.");
      return false;
    }
    if (!confirm(`Delete material "${editing.name}"?`)) return false;
    setErr("");
    try {
      await api(`/api/materials/${editing.id}`, { method: "DELETE" });
      await load();
      return true;
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      return false;
    }
  }

  async function handleToggleActiveInModal() {
    const ok = await toggleActiveInModal();
    if (ok) closeModal();
  }

  async function handleDeleteInModal() {
    const deleted = await deleteMaterialInModal();
    if (deleted) closeModal();
  }

  function getOrderSupplierId(m: Material): string | null {
    if (m.supplier_id) return m.supplier_id;
    if (m.supplier && typeof m.supplier === "string") {
      const byName = suppliers.find((s) => s.name === m.supplier || (s.name && s.name.trim() === (m.supplier || "").trim()));
      return byName?.id ?? null;
    }
    return null;
  }

  async function orderMaterial(m: Material) {
    const supplierId = getOrderSupplierId(m);
    if (!supplierId) {
      setErr("Set a supplier on this material first (edit material and choose a supplier).");
      return;
    }
    setErr("");
    setOrderingMaterialId(m.id);
    try {
      const po = await api.post<{ id: string }>("/api/purchase-orders", { supplier_id: supplierId });
      setOrderingMaterialId(null);
      if (!po?.id) {
        setErr("Failed to create purchase order: no id returned.");
        return;
      }
      const base = typeof window !== "undefined" && process.env.NEXT_PUBLIC_BASE_PATH ? process.env.NEXT_PUBLIC_BASE_PATH.replace(/\/$/, "") : "";
      setNavigateToPoUrl(`${base}/admin/purchase-orders/${po.id}?from=materials&materialId=${m.id}`);
    } catch (e: any) {
      setOrderingMaterialId(null);
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg === "Forbidden" || (e instanceof ApiError && e.status === 403)
        ? "You need admin rights to create purchase orders. Log in as an admin."
        : msg);
    }
  }

  async function deleteMaterialRow(m: Material) {
    try {
      const u = await api<any>(`/api/materials/${m.id}/usage`);
      const defaultCount = (u?.default_in_templates?.length ?? 0) + (u?.allowed_in_templates?.length ?? 0);
      if (defaultCount > 0) {
        setErr("Cannot delete: material is used in templates.");
        return;
      }
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      return;
    }
    if (!confirm(`Delete material "${m.name}"?`)) return;
    setErr("");
    try {
      await api(`/api/materials/${m.id}`, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function resolveSupplierName(m: Material) {
    return suppliers.find((s) => s.id === m.supplier_id)?.name || m.supplier || "—";
  }

  const usage = editing ? usageByMaterial[editing.id] : null;
  const inUse = usage
    ? (usage.default_in_templates?.length || 0) + (usage.allowed_in_templates?.length || 0) > 0
    : false;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Materials</h1>
          <div className="subtle">Manage materials (sheet and roll) used in templates and pricing.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" onClick={load}>Refresh</button>
          <button type="button" className="primary" onClick={openCreate}>New Material</button>
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
              placeholder="Search name, supplier, type..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="col">
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="all">All types</option>
              <option value="sheet">Sheet</option>
              <option value="roll">Roll</option>
            </select>
          </div>
          <div className="col">
            <select value={supplierFilterId} onChange={(e) => setSupplierFilterId(e.target.value)}>
              <option value="all">All suppliers</option>
              <option value="none">(no supplier)</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}{s.active ? "" : " (inactive)"}
                </option>
              ))}
            </select>
          </div>
          <div className="col" style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
              Active only
            </label>
            <button type="button" onClick={load}>Refresh</button>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 10px" }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "0 10px" }}>Name</th>
                <th style={{ padding: "0 10px" }}>Supplier</th>
                <th style={{ padding: "0 10px" }}>Cost / Size</th>
                <th style={{ padding: "0 10px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((m, index) => (
                <tr
                  key={m.id}
                  style={{
                    background: hoveredMaterialId === m.id ? "#f0f0f2" : index % 2 === 0 ? "#ffffff" : "#f8f8f8",
                    border: "1px solid #eee",
                    cursor: "pointer",
                  }}
                  onMouseEnter={() => setHoveredMaterialId(m.id)}
                  onMouseLeave={() => setHoveredMaterialId(null)}
                  onDoubleClick={() => openEdit(m)}
                >
                  <td style={{ padding: "12px 10px", borderTopLeftRadius: 12, borderBottomLeftRadius: 12 }}>
                    <div style={{ fontWeight: 600 }}>
                      {m.name} <span className="subtle">({m.type})</span>{" "}
                      {!m.active && <span className="subtle">(inactive)</span>}
                    </div>
                    {m.nominal_code && (
                      <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>{m.nominal_code}</div>
                    )}
                    {m.supplier_product_code && (
                      <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>{m.supplier_product_code}</div>
                    )}
                  </td>
                  <td style={{ padding: "12px 10px" }}>{resolveSupplierName(m)}</td>
                  <td style={{ padding: "12px 10px" }}>
                    <div className="subtle">
                      {m.type === "sheet"
                        ? "Sheet · see Sizes in Edit"
                        : `${m.roll_width_mm}mm · £${m.cost_per_lm_gbp}/lm · Min ${m.min_billable_lm}lm`}
                    </div>
                  </td>
                  <td
                    style={{ padding: "12px 10px", borderTopRightRadius: 12, borderBottomRightRadius: 12 }}
                    onClick={(e) => e.stopPropagation()}
                    onDoubleClick={(e) => e.stopPropagation()}
                  >
                    <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", alignItems: "center" }}>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          orderMaterial(m);
                        }}
                        title={getOrderSupplierId(m) ? "Order material (new PO)" : "Set a supplier on this material first"}
                        disabled={!getOrderSupplierId(m) || orderingMaterialId === m.id}
                      >
                        {orderingMaterialId === m.id ? "Creating…" : "Order"}
                      </button>
                      <button type="button" onClick={() => openEdit(m)} onDoubleClick={(e) => e.stopPropagation()}>
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); deleteMaterialRow(m); }}
                        title="Delete material"
                        style={{ padding: "4px 6px", lineHeight: 1 }}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && <div className="subtle" style={{ marginTop: 10 }}>No materials found.</div>}
      </div>

      <Modal
        open={modalOpen}
        title={editing ? "Edit Material" : "New Material"}
        onClose={closeModal}
        wide
      >
        <form
          style={{ display: "grid", gap: 16 }}
          onSubmit={(e) => {
            e.preventDefault();
            saveMaterial();
          }}
        >
          {editing && !editing.active && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: "rgba(255, 149, 0, 0.12)",
                border: "1px solid rgba(255, 149, 0, 0.3)",
                color: "#b45309",
                fontSize: 14,
              }}
            >
              This material is inactive.
            </div>
          )}

          {/* Basic */}
          <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>Basic</div>
            <div className="row">
              <div className="col">
                <label className="subtle">Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="col">
                <label className="subtle">Nominal Code</label>
                <input value={nominalCode} onChange={(e) => setNominalCode(e.target.value)} placeholder="e.g. MAT-001" />
              </div>
              <div className="col">
                <label className="subtle">Supplier Product Code</label>
                <input value={supplierProductCode} onChange={(e) => setSupplierProductCode(e.target.value)} placeholder="e.g. SUP-12345" />
              </div>
              <div className="col">
                <label className="subtle">Type</label>
                <select value={matType} onChange={(e) => setMatType(e.target.value as "sheet" | "roll")}>
                  <option value="sheet">Sheet</option>
                  <option value="roll">Roll</option>
                </select>
              </div>
              <div className="col">
                <label className="subtle">Supplier</label>
                <select
                  value={supplierId}
                  onChange={(e) => {
                    const id = e.target.value;
                    setSupplierId(id);
                    const sup = suppliers.find((s) => s.id === id);
                    setSupplierStr(sup ? sup.name : "");
                  }}
                >
                  <option value="">(none)</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}{s.active ? "" : " (inactive)"}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Roll (type-specific) — only for roll materials */}
          {matType === "roll" && (
            <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>Roll</div>
              <div className="row">
                <div className="col">
                  <label className="subtle">Roll width (mm)</label>
                  <input type="number" value={rollW} onChange={(e) => setRollW(num(e.target.value, 0))} />
                </div>
                <div className="col">
                  <label className="subtle">Cost per lm (£)</label>
                  <input type="number" step="0.01" value={costLm} onChange={(e) => setCostLm(num(e.target.value, 0))} />
                </div>
                <div className="col">
                  <label className="subtle">Min billable (lm)</label>
                  <input type="number" step="0.1" value={minLm} onChange={(e) => setMinLm(num(e.target.value, 1))} />
                </div>
              </div>
            </div>
          )}

          {/* Sizes — dedicated panel: only sizes content */}
          {editing ? (
            <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 16, fontWeight: 700 }}>Sizes</span>
                <button type="button" onClick={openAddSize} style={{ fontSize: 12, padding: "4px 8px", backgroundColor: "#e6f2ff", color: "#004080", border: "1px solid #b3d9ff" }}>+ Add Size</button>
              </div>
              {sizesLoading ? (
                <div className="subtle" style={{ fontSize: 14, padding: "12px 0" }}>Loading…</div>
              ) : (
                <>
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                      <thead>
                        <tr className="subtle" style={{ textAlign: "left" }}>
                          <th style={{ padding: "4px 6px" }}>Label</th>
                          <th style={{ padding: "4px 6px" }}>Width</th>
                          <th style={{ padding: "4px 6px" }}>Height</th>
                          <th style={{ padding: "4px 6px" }}>Cost per sheet</th>
                          <th style={{ padding: "4px 6px" }}>Active</th>
                          <th style={{ padding: "4px 6px", width: 44, textAlign: "right" }}></th>
                        </tr>
                      </thead>
                      <tbody>
                        {sizes.map((s, index) => (
                          <tr
                            key={s.id}
                            style={{ borderBottom: "1px solid #eee", background: index % 2 === 0 ? "#fff" : "#f6f6f6", cursor: "pointer" }}
                            onDoubleClick={() => openEditSize(s)}
                          >
                            <td style={{ padding: "4px 6px" }}>
                              {s.label}
                              {!s.active && <span className="subtle"> (inactive)</span>}
                            </td>
                            <td style={{ padding: "4px 6px" }}>{s.width_mm} mm</td>
                            <td style={{ padding: "4px 6px" }}>{s.height_mm} mm</td>
                            <td style={{ padding: "4px 6px" }}>
                              {s.cost_per_sheet_gbp != null ? `£${s.cost_per_sheet_gbp}` : "—"}
                            </td>
                            <td style={{ padding: "4px 6px" }}>{s.active ? "Yes" : "No"}</td>
                            <td style={{ padding: "4px 6px", textAlign: "right" }} onDoubleClick={(e) => e.stopPropagation()}>
                              <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); deleteSizeRow(s); }}
                                title="Delete size"
                                style={{ padding: "4px 6px", lineHeight: 1 }}
                              >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></svg>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {sizes.length === 0 && !sizesLoading && (
                    <div className="subtle" style={{ marginTop: 8, fontSize: 14 }}>No sizes. Add sheet sizes with dimensions and cost per sheet.</div>
                  )}
                </>
              )}
            </div>
          ) : (
            <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>Sizes</div>
              <div className="subtle" style={{ fontSize: 14 }}>Save material first to add sizes.</div>
            </div>
          )}

          {/* Cutter tools (for finishing speed) */}
          <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <span style={{ fontSize: 16, fontWeight: 700 }}>Finishing</span>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  const firstKey = cutterToolsOptions[0]?.key ?? "";
                  if (firstKey) setCutterTools((prev) => [...prev, { key: firstKey, default: prev.length === 0 }]);
                }}
                disabled={cutterToolsOptions.length === 0}
                title={cutterToolsOptions.length === 0 ? "Add tools to a cutter machine in Machines admin" : "Add cutter tool"}
                style={{ fontSize: 12, padding: "4px 8px", backgroundColor: "#e6f2ff", color: "#004080", border: "1px solid #b3d9ff" }}
              >
                + Add tool
              </button>
            </div>
            {cutterTools.length > 0 ? (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr className="subtle" style={{ textAlign: "left" }}>
                      <th style={{ padding: "4px 6px" }}>Tool</th>
                      <th style={{ padding: "4px 6px", width: 80 }}>Default</th>
                      <th style={{ padding: "4px 6px", width: 80, textAlign: "right" }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {cutterTools.map((entry, index) => (
                      <tr key={`${entry.key}-${index}`} style={{ borderBottom: "1px solid #eee" }}>
                        <td style={{ padding: "6px" }}>
                          <select
                            value={entry.key}
                            onChange={(e) => {
                              const newKey = e.target.value;
                              const next = [...cutterTools];
                              next[index] = { ...next[index], key: newKey };
                              setCutterTools(next);
                            }}
                            disabled={cutterToolsOptions.length === 0}
                            style={{ minWidth: 140 }}
                          >
                            {cutterToolsOptions.some((o) => o.key === entry.key) ? null : (
                              <option value={entry.key}>{entry.key}</option>
                            )}
                            {cutterToolsOptions.map((opt) => (
                              <option key={opt.key} value={opt.key}>
                                {opt.name}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td style={{ padding: "6px" }}>
                          <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                            <input
                              type="radio"
                              name="cutter-default"
                              checked={entry.default}
                              onChange={() => {
                                setCutterTools((prev) =>
                                  prev.map((t, i) => ({ ...t, default: i === index }))
                                );
                              }}
                            />
                          </label>
                        </td>
                        <td style={{ padding: "6px", textAlign: "right" }}>
                          <button
                            type="button"
                            onClick={() => setCutterTools((prev) => prev.filter((_, i) => i !== index))}
                            title="Remove tool"
                            style={{ padding: "4px 6px", lineHeight: 1 }}
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></svg>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
            {cutterToolsOptions.length === 0 && (
              <div className="subtle" style={{ fontSize: 12, marginTop: 8 }}>No cutter tools. Define tools in Machines admin (cutter).</div>
            )}
          </div>

          {err && modalOpen && (
            <div style={{ color: "#c00", fontSize: 14, whiteSpace: "pre-wrap" }}>{err}</div>
          )}

          {editing && (
            <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12, background: "#fafafa" }}>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>Usage</div>
              {usage != null ? (
                <div style={{ fontSize: 14 }}>
                  <div>
                    Default in templates: {usage.default_in_templates?.length ?? 0}
                    {usage.default_in_templates?.length ? (
                      <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                        {(usage.default_in_templates || []).map((t: any) => (
                          <li key={t.id}>
                            <a href={`/admin/templates?template=${t.id}`}>{t.name}</a>
                            {t.category ? <span className="subtle"> ({t.category})</span> : null}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  <div style={{ marginTop: 8 }}>
                    Allowed in templates: {usage.allowed_in_templates?.length ?? 0}
                    {usage.allowed_in_templates?.length ? (
                      <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                        {(usage.allowed_in_templates || []).map((t: any) => (
                          <li key={t.id}>
                            <a href={`/admin/templates?template=${t.id}`}>{t.name}</a>
                            {t.category ? <span className="subtle"> ({t.category})</span> : null}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  {inUse && <div className="subtle" style={{ marginTop: 8 }}>In use</div>}
                </div>
              ) : (
                <div className="subtle" style={{ fontSize: 14 }}>Usage data unavailable.</div>
              )}
            </div>
          )}

          {/* Meta (optional) */}
          <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Meta (optional)</div>
            {!editAdvancedMeta ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <input placeholder="Family" value={meta.family ?? ""} onChange={(e) => setMeta({ ...meta, family: e.target.value })} />
                <input placeholder="Finish" value={meta.finish ?? ""} onChange={(e) => setMeta({ ...meta, finish: e.target.value })} />
                <input placeholder="Thickness (mm)" type="number" step="0.1" value={meta.thickness_mm ?? ""} onChange={(e) => setMeta({ ...meta, thickness_mm: e.target.value ? num(e.target.value) : undefined })} />
                <input placeholder="GSM" type="number" value={meta.gsm ?? ""} onChange={(e) => setMeta({ ...meta, gsm: e.target.value ? num(e.target.value) : undefined })} />
                <input placeholder="Adhesive" value={meta.adhesive ?? ""} onChange={(e) => setMeta({ ...meta, adhesive: e.target.value })} />
                <input placeholder="Fire rating" value={meta.fire_rating ?? ""} onChange={(e) => setMeta({ ...meta, fire_rating: e.target.value })} />
                <div style={{ gridColumn: "1 / -1" }}>
                  <label className="subtle">Notes</label>
                  <textarea rows={2} value={meta.notes ?? ""} onChange={(e) => setMeta({ ...meta, notes: e.target.value })} />
                </div>
              </div>
            ) : (
              <textarea rows={8} value={editMetaJson} onChange={(e) => setEditMetaJson(e.target.value)} style={{ fontFamily: "monospace", fontSize: 12 }} />
            )}
            <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
              <input
                type="checkbox"
                checked={editAdvancedMeta}
                onChange={(e) => {
                  const on = e.target.checked;
                  setEditAdvancedMeta(on);
                  if (on) setEditMetaJson(JSON.stringify(meta, null, 2));
                  else try { setMeta(JSON.parse(editMetaJson || "{}")); } catch { /* keep meta */ }
                }}
              />
              Advanced JSON
            </label>
          </div>

          {/* Supplier & defaults */}
          <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>Supplier & defaults</div>
            <div className="row">
              <div className="col">
                <label className="subtle">Waste % (0.05 = 5%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={wastePct}
                  onChange={(e) => setWastePct(num(e.target.value, 0.05))}
                />
              </div>
              <div className="col" style={{ display: "flex", alignItems: "flex-end" }}>
                <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
                  Active
                </label>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 8 }}>
            <div style={{ display: "flex", gap: 10 }}>
              {editing && (
                <>
                  <button type="button" onClick={handleToggleActiveInModal}>
                    {editing.active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={handleDeleteInModal}
                    disabled={inUse}
                    title={inUse ? "Material is used in templates" : "Delete material"}
                  >
                    Delete Material
                  </button>
                </>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={closeModal}>Cancel</button>
              <button
                type="button"
                className="primary"
                disabled={!name.trim()}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  saveMaterial();
                }}
              >
                {editing ? "Save changes" : "Create material"}
              </button>
            </div>
          </div>
        </form>
      </Modal>

      <Modal
        open={sizeModalOpen}
        title={editingSize ? "Edit Size" : "Add Size"}
        onClose={() => { setSizeModalOpen(false); setEditingSize(null); }}
        zIndex={10000}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <div className="row">
            <div className="col">
              <label className="subtle">Label</label>
              <input
                value={sizeLabel}
                onChange={(e) => setSizeLabel(e.target.value)}
                placeholder="e.g. 1220×2440"
              />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Width (mm)</label>
              <input
                type="number"
                value={sizeWidthMm || ""}
                onChange={(e) => setSizeWidthMm(num(e.target.value, 0))}
              />
            </div>
            <div className="col">
              <label className="subtle">Height (mm)</label>
              <input
                type="number"
                value={sizeHeightMm || ""}
                onChange={(e) => setSizeHeightMm(num(e.target.value, 0))}
              />
            </div>
            <div className="col">
              <label className="subtle">Cost per sheet (£)</label>
              <input
                type="number"
                step="0.01"
                value={sizeCostPerSheet === "" ? "" : sizeCostPerSheet}
                onChange={(e) => {
                  const v = e.target.value;
                  setSizeCostPerSheet(v === "" ? "" : num(v, 0));
                }}
                placeholder="Optional"
              />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Sort order</label>
              <input
                type="number"
                value={sizeSortOrder}
                onChange={(e) => setSizeSortOrder(num(e.target.value, 0))}
              />
            </div>
            <div className="col" style={{ display: "flex", alignItems: "flex-end" }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input type="checkbox" checked={sizeActive} onChange={(e) => setSizeActive(e.target.checked)} />
                Active
              </label>
            </div>
          </div>
          {err && sizeModalOpen && (
            <div style={{ color: "#c00", fontSize: 14, whiteSpace: "pre-wrap" }}>{err}</div>
          )}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
            <div>
              {editingSize && (
                <button type="button" className="danger" onClick={deleteSizeInModal}>
                  Delete
                </button>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={() => { setSizeModalOpen(false); setEditingSize(null); }}>Cancel</button>
              <button type="button" className="primary" onClick={saveSize} disabled={!sizeLabel.trim()}>
                {editingSize ? "Save" : "Create"}
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
