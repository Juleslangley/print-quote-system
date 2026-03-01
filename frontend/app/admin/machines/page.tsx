"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import Modal from "../../_components/Modal";

const CATEGORIES = [
  { value: "printer_sheet", label: "Printer (sheet)" },
  { value: "printer_roll", label: "Printer (roll)" },
  { value: "cutter", label: "Cutter" },
  { value: "finisher", label: "Finisher" },
];

const PROCESS_OPTIONS = [
  "",
  "uv_flatbed",
  "eco_solvent_roll",
  "latex_roll",
  "eco_roll",
  "router",
  "knife_cut",
  "laminator",
  "other",
];

type Machine = {
  id: string;
  name: string;
  category: string;
  process: string;
  active: boolean;
  sort_order: number;
  notes: string;
  meta: Record<string, unknown>;
};

type MachineRate = {
  id: string;
  machine_id: string;
  operation_key: string;
  unit: string;
  cost_per_unit_gbp: number;
  setup_minutes: number;
  setup_cost_gbp: number;
  min_charge_gbp: number;
  active: boolean;
  sort_order: number;
  notes: string;
};

type CutterTool = {
  key: string;
  name: string;
  speed_m_per_min: number;
};

const UNITS = ["sqm", "lm", "hour", "sheet", "job"];

export default function AdminMachinesPage() {
  const [err, setErr] = useState("");
  const [items, setItems] = useState<Machine[]>([]);
  const [q, setQ] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [activeOnly, setActiveOnly] = useState(true);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Machine | null>(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("printer_sheet");
  const [process, setProcess] = useState("");
  const [active, setActive] = useState(true);
  const [notes, setNotes] = useState("");
  const [metaAdvanced, setMetaAdvanced] = useState(false);
  const [metaJson, setMetaJson] = useState("{}");
  const [metaJsonError, setMetaJsonError] = useState<string | null>(null);
  const [sheetMaxWidthMm, setSheetMaxWidthMm] = useState("");
  const [sheetMaxHeightMm, setSheetMaxHeightMm] = useState("");
  const [rollMaxWidthMm, setRollMaxWidthMm] = useState("");
  const [speedSqmPerHour, setSpeedSqmPerHour] = useState("");
  const [defaultCoveragePct, setDefaultCoveragePct] = useState("");
  const [inkMlPerSqm100pct, setInkMlPerSqm100pct] = useState("");
  const [inkCostPerLitreGbp, setInkCostPerLitreGbp] = useState("");

  const [rates, setRates] = useState<MachineRate[]>([]);
  const [rateModalOpen, setRateModalOpen] = useState(false);
  const [editingRate, setEditingRate] = useState<MachineRate | null>(null);
  const [rateOperationKey, setRateOperationKey] = useState("");
  const [rateUnit, setRateUnit] = useState("sqm");
  const [rateCostPerUnit, setRateCostPerUnit] = useState(0);
  const [rateSetupMinutes, setRateSetupMinutes] = useState(0);
  const [rateSetupCost, setRateSetupCost] = useState(0);
  const [rateMinCharge, setRateMinCharge] = useState(0);
  const [rateActive, setRateActive] = useState(true);
  const [rateNotes, setRateNotes] = useState("");

  const [tools, setTools] = useState<CutterTool[]>([]);

  function resetForm() {
    setName("");
    setCategory("printer_sheet");
    setProcess("");
    setActive(true);
    setNotes("");
    setMetaAdvanced(false);
    setMetaJson("{}");
    setMetaJsonError(null);
    setSheetMaxWidthMm("");
    setSheetMaxHeightMm("");
    setRollMaxWidthMm("");
    setSpeedSqmPerHour("");
    setDefaultCoveragePct("");
    setInkMlPerSqm100pct("");
    setInkCostPerLitreGbp("");
    setTools([]);
  }

  function metaToForm(m: Record<string, unknown> | null) {
    if (!m) {
      setSheetMaxWidthMm("");
      setSheetMaxHeightMm("");
      setRollMaxWidthMm("");
      setSpeedSqmPerHour("");
      setDefaultCoveragePct("");
      setInkMlPerSqm100pct("");
      setInkCostPerLitreGbp("");
      setMetaJson("{}");
      setTools([]);
      return;
    }
    const ma = m as Record<string, unknown>;
    setSheetMaxWidthMm(String(ma.sheet_max_width_mm ?? ""));
    setSheetMaxHeightMm(String(ma.sheet_max_height_mm ?? ""));
    setRollMaxWidthMm(String(ma.roll_max_width_mm ?? ""));
    setSpeedSqmPerHour(String(ma.speed_sqm_per_hour ?? ""));
    setDefaultCoveragePct(String(ma.default_coverage_pct ?? ""));
    setInkMlPerSqm100pct(String(ma.ink_ml_per_sqm_100pct ?? ""));
    setInkCostPerLitreGbp(String(ma.ink_cost_per_litre_gbp ?? ""));
    setMetaJson(JSON.stringify(m, null, 2));
    const rawTools = ma.tools;
    if (Array.isArray(rawTools) && rawTools.every((t: unknown) => t !== null && typeof t === "object" && "key" in (t as object) && "speed_m_per_min" in (t as object))) {
      setTools(rawTools.map((t: unknown) => {
        const o = t as Record<string, unknown>;
        return { key: String(o.key ?? ""), name: String(o.name ?? o.key ?? ""), speed_m_per_min: Number(o.speed_m_per_min) || 0 };
      }));
    } else {
      setTools([]);
    }
  }

  function validateMetaJson(): string | null {
    if (!metaAdvanced) return null;
    const s = (metaJson || "").trim();
    if (!s) return null;
    try {
      const parsed = JSON.parse(s);
      if (parsed !== null && typeof parsed !== "object") return "Meta must be a JSON object";
      return null;
    } catch (e) {
      return e instanceof SyntaxError ? e.message : "Invalid JSON";
    }
  }

  function formToMeta(): Record<string, unknown> {
    if (metaAdvanced) {
      try {
        const parsed = JSON.parse(metaJson || "{}");
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch {
        return {};
      }
    }
    const m: Record<string, unknown> = {};
    if (sheetMaxWidthMm.trim() !== "") m.sheet_max_width_mm = Number(sheetMaxWidthMm) || 0;
    if (sheetMaxHeightMm.trim() !== "") m.sheet_max_height_mm = Number(sheetMaxHeightMm) || 0;
    if (rollMaxWidthMm.trim() !== "") m.roll_max_width_mm = Number(rollMaxWidthMm) || 0;
    if (speedSqmPerHour.trim() !== "") m.speed_sqm_per_hour = Number(speedSqmPerHour) || 0;
    if (defaultCoveragePct.trim() !== "") m.default_coverage_pct = Number(defaultCoveragePct) || 0;
    if (inkMlPerSqm100pct.trim() !== "") m.ink_ml_per_sqm_100pct = Number(inkMlPerSqm100pct) || 0;
    if (inkCostPerLitreGbp.trim() !== "") m.ink_cost_per_litre_gbp = Number(inkCostPerLitreGbp) || 0;
    if (category === "cutter" && tools.length > 0) {
      m.tools = tools.map((t) => ({ key: t.key.trim() || t.key, name: t.name.trim() || t.key, speed_m_per_min: t.speed_m_per_min }));
    }
    return m;
  }

  function openCreate() {
    setEditing(null);
    resetForm();
    setRates([]);
    setModalOpen(true);
  }

  function openEdit(m: Machine) {
    setEditing(m);
    setName(m.name || "");
    setCategory(m.category || "printer_sheet");
    setProcess(m.process || "");
    setActive(!!m.active);
    setNotes(m.notes || "");
    setMetaAdvanced(false);
    metaToForm(m.meta || null);
    setModalOpen(true);
    loadRates(m.id);
  }

  function isMachineFormDirty(): boolean {
    if (editing) {
      const prevMeta = editing.meta && typeof editing.meta === "object" ? editing.meta : {};
      return (
        (name || "").trim() !== (editing.name || "").trim() ||
        category !== (editing.category || "printer_sheet") ||
        (process || "").trim() !== (editing.process || "").trim() ||
        active !== !!editing.active ||
        (notes || "").trim() !== (editing.notes || "").trim() ||
        JSON.stringify(formToMeta()) !== JSON.stringify(prevMeta)
      );
    }
    // New machine: dirty if user has entered anything
    return (name || "").trim() !== "" || (process || "").trim() !== "" ||
      (notes || "").trim() !== "" || tools.length > 0 ||
      sheetMaxWidthMm !== "" || sheetMaxHeightMm !== "" || rollMaxWidthMm !== "" ||
      speedSqmPerHour !== "" || defaultCoveragePct !== "" || inkMlPerSqm100pct !== "" || inkCostPerLitreGbp !== "";
  }

  function isRateFormDirty(): boolean {
    if (editingRate) {
    return (
      (rateOperationKey || "").trim() !== (editingRate.operation_key || "").trim() ||
      rateUnit !== (editingRate.unit || "sqm") ||
      rateCostPerUnit !== (editingRate.cost_per_unit_gbp ?? 0) ||
      rateSetupMinutes !== (editingRate.setup_minutes ?? 0) ||
      rateSetupCost !== (editingRate.setup_cost_gbp ?? 0) ||
      rateMinCharge !== (editingRate.min_charge_gbp ?? 0) ||
      rateActive !== !!editingRate.active ||
      (rateNotes || "").trim() !== (editingRate.notes || "").trim()
    );
    }
    // New rate: dirty if user has entered anything
    return (rateOperationKey || "").trim() !== "" || rateCostPerUnit !== 0 ||
      rateSetupMinutes !== 0 || rateSetupCost !== 0 || rateMinCharge !== 0 ||
      (rateNotes || "").trim() !== "";
  }

  function doCloseModal() {
    setModalOpen(false);
    setEditing(null);
    setRateModalOpen(false);
    setEditingRate(null);
  }

  function doCloseRateModal() {
    setRateModalOpen(false);
    setEditingRate(null);
  }

  const machineModalRequestCloseRef = useRef<(() => void) | null>(null);
  const rateModalRequestCloseRef = useRef<(() => void) | null>(null);

  async function loadRates(machineId: string) {
    try {
      const list = await api<MachineRate[]>(`/api/machines/${machineId}/rates`);
      setRates(list ?? []);
    } catch {
      setRates([]);
    }
  }

  async function load() {
    setErr("");
    try {
      const url = activeOnly
        ? "/api/machines"
        : "/api/machines?include_inactive=true";
      const list = await api<Machine[]>(url);
      setItems(list ?? []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, [activeOnly]);

  useEffect(() => {
    if (!metaAdvanced) {
      setMetaJsonError(null);
      return;
    }
    const s = (metaJson || "").trim();
    if (!s) {
      setMetaJsonError(null);
      return;
    }
    try {
      const parsed = JSON.parse(s);
      if (parsed !== null && typeof parsed !== "object") {
        setMetaJsonError("Meta must be a JSON object");
      } else {
        setMetaJsonError(null);
      }
    } catch (e) {
      setMetaJsonError(e instanceof SyntaxError ? e.message : "Invalid JSON");
    }
  }, [metaAdvanced, metaJson]);

  const filtered = useMemo(() => {
    const text = q.trim().toLowerCase();
    return (items || [])
      .filter((m) => {
        if (activeOnly && !m.active) return false;
        if (categoryFilter !== "all" && m.category !== categoryFilter) return false;
        if (!text) return true;
        return (
          (m.name || "").toLowerCase().includes(text) ||
          (m.process || "").toLowerCase().includes(text) ||
          (m.notes || "").toLowerCase().includes(text)
        );
      })
      .sort((a, b) => (a.sort_order !== b.sort_order ? a.sort_order - b.sort_order : (a.name || "").localeCompare(b.name || "")));
  }, [items, q, categoryFilter, activeOnly]);

  async function saveMachine() {
    setErr("");
    if (metaAdvanced) {
      const jsonErr = validateMetaJson();
      if (jsonErr) {
        setErr(`Invalid JSON: ${jsonErr}`);
        setMetaJsonError(jsonErr);
        throw new Error(`Invalid JSON: ${jsonErr}`);
      }
    }
    try {
      const formMeta = formToMeta();
      // When editing, merge existing meta with form fields so backend preserves keys we don't edit (ink, speed, etc.)
      const meta = editing ? { ...(editing.meta || {}), ...formMeta } : formMeta;
      const payload = {
        name: name.trim(),
        category,
        process: process.trim(),
        active,
        notes: notes.trim(),
        meta,
      };
      if (!payload.name) {
        setErr("Name is required");
        return;
      }
      if (editing) {
        await api(`/api/machines/${editing.id}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await api("/api/machines", { method: "POST", body: JSON.stringify(payload) });
      }
      doCloseModal();
      await load();
    } catch (e: any) {
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg);
      throw e;
    }
  }

  async function handleToggleActive() {
    if (!editing?.id) return;
    setErr("");
    try {
      const updated = await api<Machine>(`/api/machines/${editing.id}`, {
        method: "PUT",
        body: JSON.stringify({ active: !editing.active }),
      });
      setEditing(updated);
      setActive(updated.active);
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function handleDeactivate() {
    if (!editing?.id) return;
    setErr("");
    try {
      await api(`/api/machines/${editing.id}`, { method: "DELETE" });
      doCloseModal();
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function openAddRate() {
    setEditingRate(null);
    setRateOperationKey("");
    setRateUnit("sqm");
    setRateCostPerUnit(0);
    setRateSetupMinutes(0);
    setRateSetupCost(0);
    setRateMinCharge(0);
    setRateActive(true);
    setRateNotes("");
    setRateModalOpen(true);
  }

  function openEditRate(r: MachineRate) {
    setEditingRate(r);
    setRateOperationKey(r.operation_key || "");
    setRateUnit(r.unit || "sqm");
    setRateCostPerUnit(r.cost_per_unit_gbp ?? 0);
    setRateSetupMinutes(r.setup_minutes ?? 0);
    setRateSetupCost(r.setup_cost_gbp ?? 0);
    setRateMinCharge(r.min_charge_gbp ?? 0);
    setRateActive(!!r.active);
    setRateNotes(r.notes || "");
    setRateModalOpen(true);
  }

  async function saveRate() {
    if (!editing?.id) return;
    setErr("");
    try {
      if (editingRate) {
        await api(`/api/machine-rates/${editingRate.id}`, {
          method: "PUT",
          body: JSON.stringify({
            operation_key: rateOperationKey.trim(),
            unit: rateUnit,
            cost_per_unit_gbp: rateCostPerUnit,
            setup_minutes: rateSetupMinutes,
            setup_cost_gbp: rateSetupCost,
            min_charge_gbp: rateMinCharge,
            active: rateActive,
            notes: rateNotes.trim(),
          }),
        });
      } else {
        await api("/api/machine-rates", {
          method: "POST",
          body: JSON.stringify({
            machine_id: editing.id,
            operation_key: rateOperationKey.trim(),
            unit: rateUnit,
            cost_per_unit_gbp: rateCostPerUnit,
            setup_minutes: rateSetupMinutes,
            setup_cost_gbp: rateSetupCost,
            min_charge_gbp: rateMinCharge,
            active: rateActive,
            notes: rateNotes.trim(),
          }),
        });
      }
      doCloseRateModal();
      await loadRates(editing.id);
    } catch (e: any) {
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg);
      throw e;
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Machines</h1>
          <div className="subtle">Print/cut equipment (Nyala, HP roll, Zünd, etc.) with machine-specific rate tables.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" onClick={load}>Refresh</button>
          <button type="button" className="primary" onClick={openCreate}>New Machine</button>
        </div>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#c00", whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {err}
        </div>
      )}

      <div className="card section">
        <div className="row" style={{ alignItems: "center" }}>
          <div className="col">
            <input placeholder="Search name, process, notes..." value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="col">
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="all">All categories</option>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="col" style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
              Active only
            </label>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "6px 8px" }}>Name</th>
                <th style={{ padding: "6px 8px" }}>Category</th>
                <th style={{ padding: "6px 8px" }}>Process</th>
                <th style={{ padding: "6px 8px" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((m, index) => (
                <tr
                  key={m.id}
                  style={{
                    background: hoveredId === m.id ? "#f0f0f2" : index % 2 === 0 ? "#fff" : "#f8f8f8",
                    border: "1px solid #eee",
                    cursor: "pointer",
                  }}
                  onMouseEnter={() => setHoveredId(m.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onDoubleClick={() => openEdit(m)}
                >
                  <td style={{ padding: "8px" }}>
                    {m.name}
                    {!m.active && (
                      <span
                        style={{
                          marginLeft: 8,
                          fontSize: 11,
                          padding: "2px 6px",
                          borderRadius: 4,
                          background: "#f0f0f2",
                          color: "#6e6e73",
                          fontWeight: 500,
                        }}
                      >
                        Inactive
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "8px" }}>
                    {CATEGORIES.find((c) => c.value === m.category)?.label ?? m.category}
                  </td>
                  <td style={{ padding: "8px" }}>{m.process || "—"}</td>
                  <td style={{ padding: "8px" }}>
                    <button type="button" onClick={(e) => { e.stopPropagation(); openEdit(m); }}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="subtle" style={{ marginTop: 10 }}>No machines found.</div>
        )}
      </div>

      <Modal
        open={modalOpen}
        title={editing ? "Edit Machine" : "New Machine"}
        onClose={doCloseModal}
        wide
        isDirty={modalOpen && isMachineFormDirty()}
        onSave={saveMachine}
        requestCloseRef={machineModalRequestCloseRef}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <div className="row">
            <div className="col">
              <label className="subtle">Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Process</label>
              <select value={process} onChange={(e) => setProcess(e.target.value)} style={{ marginRight: 8 }}>
                {PROCESS_OPTIONS.map((p) => (
                  <option key={p || "blank"} value={p}>{p || "—"}</option>
                ))}
              </select>
              <input
                placeholder="Or type custom (e.g. uv_flatbed, knife_cut)"
                value={process}
                onChange={(e) => setProcess(e.target.value)}
                style={{ marginTop: 4, width: "100%" }}
              />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Notes</label>
              <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            Active
          </label>

          <div className="capabilities-section">
            <h3 className="capabilities-title">Machine Capabilities</h3>
            <p className="capabilities-subtitle">Used for production time + ink cost calculations.</p>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={metaAdvanced}
                  onChange={(e) => setMetaAdvanced(e.target.checked)}
                />
                Advanced JSON
              </label>
            </div>
            {!metaAdvanced ? (
              (() => {
                const showSheet = process === "uv_flatbed" || (category === "printer_sheet" && process !== "eco_solvent_roll" && process !== "eco_roll" && process !== "latex_roll");
                const showRoll = process === "eco_solvent_roll" || process === "eco_roll" || process === "latex_roll";
                const showProduction = category !== "cutter" && (process === "uv_flatbed" || process === "eco_solvent_roll" || process === "eco_roll" || process === "latex_roll" || category === "printer_sheet" || category === "printer_roll");
                const showInk = showProduction;
                const speed = parseFloat(speedSqmPerHour);
                const cov = parseFloat(defaultCoveragePct);
                const inkMl = parseFloat(inkMlPerSqm100pct);
                const inkCost = parseFloat(inkCostPerLitreGbp);
                const inkGbpPerSqm = (inkMl * (cov / 100) / 1000) * inkCost;
                const hasInkHelper = !isNaN(cov) && !isNaN(inkMl) && !isNaN(inkCost) && cov > 0 && inkMl > 0 && inkCost > 0;
                return (
                  <div className="capabilities-grid">
                    {(showSheet || showRoll) && (
                      <div className="capability-panel">
                        <div className="capability-panel-title">Size limits</div>
                        {showSheet && (
                          <>
                            <div className="capability-field">
                              <label className="subtle">sheet_max_width_mm (mm)</label>
                              <input
                                type="number"
                                value={sheetMaxWidthMm}
                                onChange={(e) => setSheetMaxWidthMm(e.target.value)}
                                placeholder="—"
                              />
                            </div>
                            <div className="capability-field">
                              <label className="subtle">sheet_max_height_mm (mm)</label>
                              <input
                                type="number"
                                value={sheetMaxHeightMm}
                                onChange={(e) => setSheetMaxHeightMm(e.target.value)}
                                placeholder="—"
                              />
                            </div>
                          </>
                        )}
                        {showRoll && (
                          <div className="capability-field">
                            <label className="subtle">roll_max_width_mm (mm)</label>
                            <input
                              type="number"
                              value={rollMaxWidthMm}
                              onChange={(e) => setRollMaxWidthMm(e.target.value)}
                              placeholder="—"
                            />
                          </div>
                        )}
                      </div>
                    )}
                    {showProduction && (
                      <div className="capability-panel">
                        <div className="capability-panel-title">Production model</div>
                        <div className="capability-field">
                          <label className="subtle">speed_sqm_per_hour (sqm/hr)</label>
                          <input
                            type="number"
                            min={0}
                            step={0.1}
                            value={speedSqmPerHour}
                            onChange={(e) => setSpeedSqmPerHour(e.target.value)}
                            placeholder="—"
                          />
                          {speed > 0 && (
                            <div className="capability-helper">
                              ≈ {(60 / speed).toFixed(1)} min / sqm
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    {showInk && (
                      <div className="capability-panel">
                        <div className="capability-panel-title">Ink model</div>
                        <div className="capability-field">
                          <label className="subtle">default_coverage_pct (%)</label>
                          <input
                            type="number"
                            min={0}
                            max={100}
                            step={0.1}
                            value={defaultCoveragePct}
                            onChange={(e) => setDefaultCoveragePct(e.target.value)}
                            placeholder="—"
                          />
                        </div>
                        <div className="capability-field">
                          <label className="subtle">ink_ml_per_sqm_100pct (ml)</label>
                          <input
                            type="number"
                            min={0}
                            step={0.1}
                            value={inkMlPerSqm100pct}
                            onChange={(e) => setInkMlPerSqm100pct(e.target.value)}
                            placeholder="—"
                          />
                        </div>
                        <div className="capability-field">
                          <label className="subtle">ink_cost_per_litre_gbp (£)</label>
                          <input
                            type="number"
                            min={0}
                            step={0.01}
                            value={inkCostPerLitreGbp}
                            onChange={(e) => setInkCostPerLitreGbp(e.target.value)}
                            placeholder="—"
                          />
                        </div>
                        {hasInkHelper && (
                          <div className="capability-helper">
                            Ink ≈ £{inkGbpPerSqm.toFixed(2)} / sqm @ {cov}%
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })()
            ) : (
              <>
                <textarea
                  rows={6}
                  value={metaJson}
                  onChange={(e) => {
                    const v = e.target.value;
                    setMetaJson(v);
                    if (!v.trim()) {
                      setMetaJsonError(null);
                      return;
                    }
                    try {
                      const parsed = JSON.parse(v);
                      if (parsed !== null && typeof parsed !== "object") {
                        setMetaJsonError("Meta must be a JSON object");
                      } else {
                        setMetaJsonError(null);
                      }
                    } catch (err) {
                      setMetaJsonError(err instanceof SyntaxError ? err.message : "Invalid JSON");
                    }
                  }}
                  style={{ fontFamily: "monospace", fontSize: 12, width: "100%", borderColor: metaJsonError ? "#c00" : undefined }}
                  placeholder='{"sheet_max_width_mm": 3200, ...}'
                />
                {metaJsonError && (
                  <div style={{ color: "#c00", fontSize: 12, marginTop: 6 }}>{metaJsonError}</div>
                )}
              </>
            )}
          </div>

          {category === "cutter" && !metaAdvanced && (
            <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span className="subtle" style={{ fontWeight: 600 }}>Tools (speed per m)</span>
                <button type="button" onClick={() => setTools((prev) => [...prev, { key: "", name: "", speed_m_per_min: 0 }])}>Add tool</button>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr className="subtle" style={{ textAlign: "left" }}>
                      <th style={{ padding: "4px 6px" }}>Key</th>
                      <th style={{ padding: "4px 6px" }}>Name</th>
                      <th style={{ padding: "4px 6px" }}>Speed (m/min)</th>
                      <th style={{ padding: "4px 6px" }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {tools.map((t, idx) => (
                      <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                        <td style={{ padding: "4px 6px" }}>
                          <input
                            value={t.key}
                            onChange={(e) => setTools((prev) => prev.map((x, i) => (i === idx ? { ...x, key: e.target.value } : x)))}
                            placeholder="e.g. cut"
                            style={{ width: "100%", maxWidth: 120 }}
                          />
                        </td>
                        <td style={{ padding: "4px 6px" }}>
                          <input
                            value={t.name}
                            onChange={(e) => setTools((prev) => prev.map((x, i) => (i === idx ? { ...x, name: e.target.value } : x)))}
                            placeholder="e.g. Cut"
                            style={{ width: "100%", maxWidth: 140 }}
                          />
                        </td>
                        <td style={{ padding: "4px 6px" }}>
                          <input
                            type="number"
                            step="0.1"
                            min={0}
                            value={t.speed_m_per_min}
                            onChange={(e) => setTools((prev) => prev.map((x, i) => (i === idx ? { ...x, speed_m_per_min: parseFloat(e.target.value) || 0 } : x)))}
                            style={{ width: 80 }}
                          />
                        </td>
                        <td style={{ padding: "4px 6px" }}>
                          <button type="button" onClick={() => setTools((prev) => prev.filter((_, i) => i !== idx))}>Remove</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {tools.length === 0 && (
                  <div className="subtle" style={{ marginTop: 6 }}>No tools. Add tools to define cut/route/crease speeds for this cutter.</div>
                )}
              </div>
            </div>
          )}

          {editing && (
            <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span className="subtle" style={{ fontWeight: 600 }}>Rates</span>
                <button type="button" onClick={openAddRate}>Add rate</button>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr className="subtle" style={{ textAlign: "left" }}>
                      <th style={{ padding: "4px 6px" }}>Operation</th>
                      <th style={{ padding: "4px 6px" }}>Unit</th>
                      <th style={{ padding: "4px 6px" }}>Cost/unit</th>
                      <th style={{ padding: "4px 6px" }}>Setup min</th>
                      <th style={{ padding: "4px 6px" }}>Min charge</th>
                      <th style={{ padding: "4px 6px" }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rates.map((r) => (
                      <tr key={r.id} style={{ borderBottom: "1px solid #eee" }}>
                        <td style={{ padding: "4px 6px" }}>
                          {r.operation_key}
                          {!r.active && <span className="subtle"> (inactive)</span>}
                        </td>
                        <td style={{ padding: "4px 6px" }}>{r.unit}</td>
                        <td style={{ padding: "4px 6px" }}>£{r.cost_per_unit_gbp}</td>
                        <td style={{ padding: "4px 6px" }}>{r.setup_minutes}</td>
                        <td style={{ padding: "4px 6px" }}>£{r.min_charge_gbp}</td>
                        <td style={{ padding: "4px 6px" }}>
                          <button type="button" onClick={() => openEditRate(r)}>Edit</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {rates.length === 0 && (
                  <div className="subtle" style={{ marginTop: 6 }}>No rates. Add one to define cost per unit, setup, min charge.</div>
                )}
              </div>
            </div>
          )}

          {err && modalOpen && (
            <div style={{ color: "#c00", fontSize: 14, whiteSpace: "pre-wrap" }}>{err}</div>
          )}

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 8 }}>
            <div style={{ display: "flex", gap: 10 }}>
              {editing && (
                editing.active ? (
                  <button type="button" className="danger" onClick={handleDeactivate} title="Deactivate machine (keeps history)">
                    Deactivate
                  </button>
                ) : (
                  <button type="button" onClick={handleToggleActive} title="Reactivate machine">
                    Activate
                  </button>
                )
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={() => machineModalRequestCloseRef.current?.()}>Cancel</button>
              <button type="button" className="primary" onClick={saveMachine} disabled={!name.trim() || (metaAdvanced && !!metaJsonError)}>
                {editing ? "Save" : "Create"}
              </button>
            </div>
          </div>
        </div>
      </Modal>

      <Modal
        open={rateModalOpen}
        title={editingRate ? "Edit Rate" : "Add Rate"}
        onClose={doCloseRateModal}
        isDirty={rateModalOpen && isRateFormDirty()}
        onSave={saveRate}
        requestCloseRef={rateModalRequestCloseRef}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <div className="row">
            <div className="col">
              <label className="subtle">Operation key</label>
              <input
                value={rateOperationKey}
                onChange={(e) => setRateOperationKey(e.target.value)}
                placeholder="e.g. print_uv, cut_zund"
              />
            </div>
            <div className="col">
              <label className="subtle">Unit</label>
              <select value={rateUnit} onChange={(e) => setRateUnit(e.target.value)}>
                {UNITS.map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Cost per unit (£)</label>
              <input
                type="number"
                step="0.01"
                value={rateCostPerUnit}
                onChange={(e) => setRateCostPerUnit(parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="col">
              <label className="subtle">Setup (minutes)</label>
              <input
                type="number"
                step="0.1"
                value={rateSetupMinutes}
                onChange={(e) => setRateSetupMinutes(parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="col">
              <label className="subtle">Setup cost (£)</label>
              <input
                type="number"
                step="0.01"
                value={rateSetupCost}
                onChange={(e) => setRateSetupCost(parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="col">
              <label className="subtle">Min charge (£)</label>
              <input
                type="number"
                step="0.01"
                value={rateMinCharge}
                onChange={(e) => setRateMinCharge(parseFloat(e.target.value) || 0)}
              />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Notes</label>
              <input value={rateNotes} onChange={(e) => setRateNotes(e.target.value)} />
            </div>
          </div>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={rateActive} onChange={(e) => setRateActive(e.target.checked)} />
            Active
          </label>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
            <button type="button" onClick={() => rateModalRequestCloseRef.current?.()}>Cancel</button>
            <button type="button" className="primary" onClick={saveRate} disabled={!rateOperationKey.trim()}>
              {editingRate ? "Save" : "Create"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
