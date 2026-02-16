"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import Modal from "../../_components/Modal";

type Material = any;

type MaterialSize = {
  id: string;
  material_id: string;
  label: string;
  width_mm: number;
  height_mm: number | null;
  cost_per_sheet_gbp: number | null;
  cost_per_lm_gbp: number | null;
  length_m: number | null;
  custom_length_available?: boolean;
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
  const [sizeHeightMm, setSizeHeightMm] = useState<number | "">("");
  const [sizeCostPerSheet, setSizeCostPerSheet] = useState<number | "">("");
  const [sizeCostPerLm, setSizeCostPerLm] = useState<number | "">("");
  const [sizeLengthM, setSizeLengthM] = useState<number | "">("");
  const [sizeCustomLengthAvailable, setSizeCustomLengthAvailable] = useState(false);
  const [sizeActive, setSizeActive] = useState(true);
  const [sizeSortOrder, setSizeSortOrder] = useState(0);

  const materialModalRequestCloseRef = useRef<(() => void) | null>(null);
  const sizeModalRequestCloseRef = useRef<(() => void) | null>(null);

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

  const sortedSizes = useMemo(() => {
    const list = [...sizes];
    if (matType === "roll") {
      list.sort((a, b) => {
        const wA = Number(a.width_mm) || 0;
        const wB = Number(b.width_mm) || 0;
        if (wA !== wB) return wA - wB;
        const lA = a.length_m != null ? Number(a.length_m) : Infinity;
        const lB = b.length_m != null ? Number(b.length_m) : Infinity;
        return lA - lB;
      });
    } else {
      list.sort((a, b) => {
        const wA = Number(a.width_mm) || 0;
        const wB = Number(b.width_mm) || 0;
        if (wA !== wB) return wA - wB;
        const hA = a.height_mm != null ? Number(a.height_mm) : Infinity;
        const hB = b.height_mm != null ? Number(b.height_mm) : Infinity;
        return hA - hB;
      });
    }
    return list;
  }, [sizes, matType]);

  useEffect(() => {
    load();
  }, []);

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

  function isMaterialFormDirty(): boolean {
    if (editing) {
      const sup = suppliers.find((s) => s.id === editing.supplier_id);
      const prevSupplierStr = sup ? sup.name : editing.supplier || "";
      if (name !== (editing.name || "")) return true;
      if (nominalCode !== (editing.nominal_code ?? "")) return true;
      if (supplierProductCode !== (editing.supplier_product_code ?? "")) return true;
      if (matType !== (editing.type === "roll" ? "roll" : "sheet")) return true;
      if (supplierId !== (editing.supplier_id || "")) return true;
      if (supplierStr !== prevSupplierStr) return true;
      if (num(wastePct) !== num(editing.waste_pct_default, 0.05)) return true;
      if (active !== !!editing.active) return true;
      const rawMeta = editing.meta && typeof editing.meta === "object" ? (editing.meta as any) : {};
      const prevTools = rawMeta.cutter_tools;
      const prevArr = Array.isArray(prevTools) && prevTools.length > 0
        ? prevTools.filter((t: any) => t && typeof t === "object" && typeof t.key === "string").map((t: any) => ({ key: String(t.key), default: !!t.default }))
        : rawMeta.cutter_tool_key ? [{ key: String(rawMeta.cutter_tool_key), default: true }] : [];
      if (cutterTools.length !== prevArr.length || cutterTools.some((t, i) => (prevArr[i]?.key !== t.key || prevArr[i]?.default !== t.default))) return true;
      const prevMeta = editing.meta && typeof editing.meta === "object" ? { ...(editing.meta as object) } : {};
      delete (prevMeta as any).cutter_tools;
      delete (prevMeta as any).cutter_tool_key;
      const currMeta = editAdvancedMeta ? (() => { try { return JSON.parse(editMetaJson || "{}"); } catch { return {}; } })() : meta;
      if (JSON.stringify(currMeta) !== JSON.stringify(prevMeta)) return true;
      return false;
    }
    // New material: dirty if user has entered anything
    return name.trim() !== "" || nominalCode.trim() !== "" || supplierProductCode.trim() !== "" ||
      matType !== "sheet" || wastePct !== 0.05 || !active ||
      (Object.keys(meta).length > 0 && JSON.stringify(meta) !== "{}") || cutterTools.length > 0;
  }

  function isSizeFormDirty(): boolean {
    if (editingSize) {
      if (sizeLabel !== (editingSize.label || "")) return true;
      if (num(sizeWidthMm) !== num(editingSize.width_mm, 0)) return true;
      if (matType === "roll") {
        const lenCur = sizeLengthM === "" ? null : num(sizeLengthM, 0);
        const lenPrev = editingSize.length_m ?? null;
        if (lenCur !== lenPrev) return true;
        const clCur = sizeCostPerLm === "" ? null : num(sizeCostPerLm, 0);
        const clPrev = editingSize.cost_per_lm_gbp ?? null;
        if (clCur !== clPrev) return true;
      } else {
        const hCur = sizeHeightMm === "" ? null : num(sizeHeightMm, 0);
        const hPrev = editingSize.height_mm ?? null;
        if (hCur !== hPrev) return true;
        const csCur = sizeCostPerSheet === "" ? null : num(sizeCostPerSheet, 0);
        const csPrev = editingSize.cost_per_sheet_gbp ?? null;
        if (csCur !== csPrev) return true;
      }
      if (sizeActive !== !!editingSize.active) return true;
      if (sizeSortOrder !== (editingSize.sort_order ?? 0)) return true;
      if (matType === "roll" && sizeCustomLengthAvailable !== !!((editingSize as MaterialSize).custom_length_available)) return true;
      return false;
    }
    return sizeLabel.trim() !== "" || sizeWidthMm !== 0 || sizeHeightMm !== "" || sizeCostPerSheet !== "" ||
      sizeCostPerLm !== "" || sizeLengthM !== "" || sizeCustomLengthAvailable || !sizeActive || sizeSortOrder !== sizes.length;
  }

  function closeModal() {
    setModalOpen(false);
    setEditing(null);
    setSizeModalOpen(false);
    setEditingSize(null);
  }

  function closeSizeModalOnly() {
    setSizeModalOpen(false);
    setEditingSize(null);
  }

  function openAddSize() {
    setEditingSize(null);
    setSizeLabel("");
    setSizeWidthMm(0);
    setSizeHeightMm("");
    setSizeCostPerSheet("");
    setSizeCostPerLm("");
    setSizeLengthM("");
    setSizeCustomLengthAvailable(false);
    setSizeActive(true);
    setSizeSortOrder(sizes.length);
    setSizeModalOpen(true);
  }

  function openEditSize(s: MaterialSize) {
    setEditingSize(s);
    setSizeLabel(s.label || "");
    setSizeWidthMm(num(s.width_mm, 0));
    setSizeHeightMm(s.height_mm != null ? s.height_mm : "");
    setSizeCostPerSheet(s.cost_per_sheet_gbp != null ? s.cost_per_sheet_gbp : "");
    setSizeCostPerLm(s.cost_per_lm_gbp != null ? s.cost_per_lm_gbp : "");
    setSizeLengthM(s.length_m != null ? s.length_m : "");
    setSizeCustomLengthAvailable(!!(s as MaterialSize).custom_length_available);
    setSizeActive(!!s.active);
    setSizeSortOrder(s.sort_order ?? 0);
    setSizeModalOpen(true);
  }

  async function saveSize() {
    if (!editing?.id) return;
    setErr("");
    try {
      const isRoll = matType === "roll";
      const costSheet = sizeCostPerSheet === "" ? null : num(sizeCostPerSheet, 0);
      const costLm = sizeCostPerLm === "" ? null : num(sizeCostPerLm, 0);
      const heightVal = sizeHeightMm === "" ? null : num(sizeHeightMm, 0);
      const lengthVal = sizeLengthM === "" ? null : num(sizeLengthM, 0);
      const payload = {
        label: sizeLabel.trim(),
        width_mm: sizeWidthMm,
        height_mm: isRoll ? null : heightVal,
        cost_per_sheet_gbp: isRoll ? null : costSheet,
        cost_per_lm_gbp: isRoll ? costLm : null,
        length_m: isRoll ? lengthVal : null,
        custom_length_available: isRoll ? sizeCustomLengthAvailable : false,
        active: sizeActive,
        sort_order: sizeSortOrder,
      };
      if (editingSize) {
        await api(`/api/material-sizes/${editingSize.id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await api("/api/material-sizes", {
          method: "POST",
          body: JSON.stringify({ ...payload, material_id: editing.id }),
        });
      }
      setSizeModalOpen(false);
      setEditingSize(null);
      await loadSizes(editing.id);
    } catch (e: any) {
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg);
      throw e;
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
        payload.roll_width_mm = null;
        payload.cost_per_lm_gbp = null;
        payload.min_billable_lm = null;
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
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg);
      throw e;
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
      const base = typeof window !== "undefined" && process.env.NEXT_PUBLIC_BASE_PATH ? String(process.env.NEXT_PUBLIC_BASE_PATH).replace(/\/$/, "") : "";
      window.location.href = `${base}/admin/purchase-orders/${po.id}?from=materials&materialId=${m.id}`;
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
                        : "Roll · see Roll widths in Edit"}
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
        isDirty={modalOpen && isMaterialFormDirty()}
        onSave={saveMaterial}
        requestCloseRef={materialModalRequestCloseRef}
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

          {/* Sizes — dedicated panel: only sizes content */}
          {editing ? (
            <div style={{ border: "1px solid #e5e5e7", borderRadius: 12, padding: 14, background: "#fafafa" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 16, fontWeight: 700 }}>{matType === "roll" ? "Roll widths" : "Sizes"}</span>
                <button type="button" onClick={(e) => { e.preventDefault(); openAddSize(); }} style={{ fontSize: 12, padding: "4px 8px", backgroundColor: "#e6f2ff", color: "#004080", border: "1px solid #b3d9ff" }}>+ Add {matType === "roll" ? "Width" : "Size"}</button>
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
                          <th style={{ padding: "4px 6px" }}>Width (mm)</th>
                          {matType === "roll" && <th style={{ padding: "4px 6px" }}>Length (m)</th>}
                          {matType === "sheet" && <th style={{ padding: "4px 6px" }}>Height (mm)</th>}
                          <th style={{ padding: "4px 6px" }}>{matType === "roll" ? "Cost per lm (£)" : "Cost per sheet (£)"}</th>
                          <th style={{ padding: "4px 6px" }}>Active</th>
                          <th style={{ padding: "4px 6px", width: 44, textAlign: "right" }}></th>
                        </tr>
                      </thead>
                      <tbody>
                        {sortedSizes.map((s, index) => (
                          <tr
                            key={s.id}
                            style={{ borderBottom: "1px solid #eee", background: index % 2 === 0 ? "#fff" : "#f6f6f6", cursor: "pointer" }}
                            onDoubleClick={() => openEditSize(s)}
                          >
                            <td style={{ padding: "4px 6px" }}>
                              {s.label}
                              {!s.active && <span className="subtle"> (inactive)</span>}
                            </td>
                            <td style={{ padding: "4px 6px" }}>{s.width_mm}</td>
                            {matType === "roll" && <td style={{ padding: "4px 6px" }}>{s.length_m ?? "—"}</td>}
                            {matType === "sheet" && <td style={{ padding: "4px 6px" }}>{s.height_mm ?? "—"}</td>}
                            <td style={{ padding: "4px 6px" }}>
                              {matType === "roll"
                                ? (s.cost_per_lm_gbp != null ? `£${s.cost_per_lm_gbp}` : "—")
                                : (s.cost_per_sheet_gbp != null ? `£${s.cost_per_sheet_gbp}` : "—")}
                            </td>
                            <td style={{ padding: "4px 6px" }}>{s.active ? "Yes" : "No"}</td>
                            <td style={{ padding: "4px 6px", textAlign: "right" }} onDoubleClick={(e) => e.stopPropagation()}>
                              <button
                                type="button"
                                onClick={(e) => { e.preventDefault(); e.stopPropagation(); deleteSizeRow(s); }}
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
                  {sortedSizes.length === 0 && !sizesLoading && (
                    <div className="subtle" style={{ marginTop: 8, fontSize: 14 }}>
                      {matType === "roll" ? "No roll widths. Add widths (e.g. 1200, 1370, 1600 mm) with cost per lm." : "No sizes. Add sheet sizes with dimensions and cost per sheet."}
                    </div>
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
              <button type="button" onClick={() => materialModalRequestCloseRef.current?.()}>Cancel</button>
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
        title={editingSize ? (matType === "roll" ? "Edit Roll Width" : "Edit Size") : (matType === "roll" ? "Add Roll Width" : "Add Size")}
        onClose={closeSizeModalOnly}
        wide
        zIndex={10000}
        isDirty={sizeModalOpen && isSizeFormDirty()}
        onSave={saveSize}
        requestCloseRef={sizeModalRequestCloseRef}
      >
        <form
          style={{ display: "grid", gap: 12 }}
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            saveSize();
          }}
        >
          <div className="row">
            <div className="col">
              <label className="subtle">Label</label>
              <input
                value={sizeLabel}
                onChange={(e) => setSizeLabel(e.target.value)}
                placeholder={matType === "roll" ? "e.g. 1200mm" : "e.g. 1220×2440"}
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
                placeholder={matType === "roll" ? "e.g. 1200, 1370, 1600" : ""}
              />
            </div>
            {matType === "roll" && (
              <div className="col">
                <label className="subtle">Length (m)</label>
                <input
                  type="number"
                  step="0.1"
                  value={sizeLengthM || ""}
                  onChange={(e) => {
                    const v = e.target.value;
                    setSizeLengthM(v === "" ? "" : num(v, 0));
                  }}
                  placeholder="e.g. 20, 50"
                />
              </div>
            )}
            {matType === "sheet" && (
              <div className="col">
                <label className="subtle">Height (mm)</label>
                <input
                  type="number"
                  value={sizeHeightMm || ""}
                  onChange={(e) => {
                    const v = e.target.value;
                    setSizeHeightMm(v === "" ? "" : num(v, 0));
                  }}
                />
              </div>
            )}
            <div className="col">
              <label className="subtle">{matType === "roll" ? "Cost per lm (£)" : "Cost per sheet (£)"}</label>
              <input
                type="number"
                step="0.01"
                value={matType === "roll" ? (sizeCostPerLm === "" ? "" : sizeCostPerLm) : (sizeCostPerSheet === "" ? "" : sizeCostPerSheet)}
                onChange={(e) => {
                  const v = e.target.value;
                  if (matType === "roll") setSizeCostPerLm(v === "" ? "" : num(v, 0));
                  else setSizeCostPerSheet(v === "" ? "" : num(v, 0));
                }}
                placeholder="Optional"
              />
            </div>
          </div>
          <div className="row" style={{ alignItems: "flex-start" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: "0 0 auto", minWidth: 0 }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", margin: 0 }}>
                <input type="checkbox" checked={sizeActive} onChange={(e) => setSizeActive(e.target.checked)} style={{ margin: 0 }} />
                Active
              </label>
              {matType === "roll" && (
                <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", whiteSpace: "nowrap", margin: 0 }}>
                  <input type="checkbox" checked={sizeCustomLengthAvailable} onChange={(e) => setSizeCustomLengthAvailable(e.target.checked)} style={{ margin: 0 }} />
                  Custom length available in PO
                </label>
              )}
            </div>
          </div>
          {err && sizeModalOpen && (
            <div style={{ color: "#c00", fontSize: 14, whiteSpace: "pre-wrap" }}>{err}</div>
          )}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
            <div>
              {editingSize && (
                <button type="button" className="danger" onClick={(e) => { e.preventDefault(); deleteSizeInModal(); }}>
                  Delete
                </button>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={() => sizeModalRequestCloseRef.current?.()}>Cancel</button>
              <button type="submit" className="primary" disabled={!sizeLabel.trim()}>
                {editingSize ? "Save" : "Create"}
              </button>
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
}
