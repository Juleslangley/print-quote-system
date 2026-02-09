"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../../../lib/api";

function Modal({
  open,
  title,
  children,
  onClose,
  wide,
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
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
        zIndex: 9999,
      }}
      onMouseDown={onClose}
    >
      <div
        style={{
          width: wide ? "min(720px, 100%)" : "min(520px, 100%)",
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

const CATEGORIES = [
  { value: "printer_sheet", label: "Printer (sheet)" },
  { value: "printer_roll", label: "Printer (roll)" },
  { value: "cutter", label: "Cutter" },
  { value: "finisher", label: "Finisher" },
];

const PROCESS_OPTIONS = [
  "",
  "uv_flatbed",
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

const UNITS = ["sqm", "lm", "hour", "sheet", "job"];

export default function AdminMachinesPage() {
  const [err, setErr] = useState("");
  const [items, setItems] = useState<Machine[]>([]);
  const [q, setQ] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [activeOnly, setActiveOnly] = useState(false);
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
  const [sheetMaxWidthMm, setSheetMaxWidthMm] = useState("");
  const [sheetMaxHeightMm, setSheetMaxHeightMm] = useState("");
  const [rollMaxWidthMm, setRollMaxWidthMm] = useState("");

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

  function resetForm() {
    setName("");
    setCategory("printer_sheet");
    setProcess("");
    setActive(true);
    setNotes("");
    setMetaJson("{}");
    setSheetMaxWidthMm("");
    setSheetMaxHeightMm("");
    setRollMaxWidthMm("");
  }

  function metaToForm(m: Record<string, unknown> | null) {
    if (!m) {
      setSheetMaxWidthMm("");
      setSheetMaxHeightMm("");
      setRollMaxWidthMm("");
      setMetaJson("{}");
      return;
    }
    setSheetMaxWidthMm(String((m as any).sheet_max_width_mm ?? ""));
    setSheetMaxHeightMm(String((m as any).sheet_max_height_mm ?? ""));
    setRollMaxWidthMm(String((m as any).roll_max_width_mm ?? ""));
    setMetaJson(JSON.stringify(m, null, 2));
  }

  function formToMeta(): Record<string, unknown> {
    if (metaAdvanced) {
      try {
        return JSON.parse(metaJson || "{}");
      } catch {
        return {};
      }
    }
    const m: Record<string, unknown> = {};
    if (sheetMaxWidthMm.trim() !== "") m.sheet_max_width_mm = Number(sheetMaxWidthMm) || 0;
    if (sheetMaxHeightMm.trim() !== "") m.sheet_max_height_mm = Number(sheetMaxHeightMm) || 0;
    if (rollMaxWidthMm.trim() !== "") m.roll_max_width_mm = Number(rollMaxWidthMm) || 0;
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
    metaToForm(m.meta || null);
    setModalOpen(true);
    loadRates(m.id);
  }

  function closeModal() {
    setModalOpen(false);
    setEditing(null);
    setRateModalOpen(false);
    setEditingRate(null);
  }

  async function loadRates(machineId: string) {
    try {
      const list = await api(`/api/machines/${machineId}/rates`);
      setRates(list || []);
    } catch {
      setRates([]);
    }
  }

  async function load() {
    setErr("");
    try {
      const list = await api("/api/machines");
      setItems(list || []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

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
    try {
      const payload = {
        name: name.trim(),
        category,
        process: process.trim(),
        active,
        notes: notes.trim(),
        meta: formToMeta(),
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
      closeModal();
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function handleToggleActive() {
    if (!editing?.id) return;
    setErr("");
    try {
      await api(`/api/machines/${editing.id}`, {
        method: "PUT",
        body: JSON.stringify({ active: !editing.active }),
      });
      setEditing((prev) => (prev ? { ...prev, active: !prev.active } : null));
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function handleDeleteInModal() {
    if (!editing?.id) return;
    if (rates.length > 0) {
      setErr("Cannot delete: machine has rate(s). Deactivate instead.");
      return;
    }
    if (!confirm(`Delete machine "${editing.name}"?`)) return;
    setErr("");
    try {
      await api(`/api/machines/${editing.id}`, { method: "DELETE" });
      closeModal();
      await load();
    } catch (e: any) {
      const res = (e as any)?.body;
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
      setRateModalOpen(false);
      setEditingRate(null);
      await loadRates(editing.id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
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
          <button onClick={load}>Refresh</button>
          <button className="primary" onClick={openCreate}>New Machine</button>
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
                    {!m.active && <span className="subtle"> (inactive)</span>}
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

      <Modal open={modalOpen} title={editing ? "Edit Machine" : "New Machine"} onClose={closeModal} wide>
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

          <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
            <div className="subtle" style={{ marginBottom: 8, fontWeight: 600 }}>Meta (capability config)</div>
            <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
              <input
                type="checkbox"
                checked={metaAdvanced}
                onChange={(e) => setMetaAdvanced(e.target.checked)}
              />
              Advanced (edit JSON)
            </label>
            {!metaAdvanced ? (
              <div className="row" style={{ gap: 12 }}>
                <div className="col">
                  <label className="subtle">Sheet max width (mm)</label>
                  <input
                    type="number"
                    value={sheetMaxWidthMm}
                    onChange={(e) => setSheetMaxWidthMm(e.target.value)}
                    placeholder="—"
                  />
                </div>
                <div className="col">
                  <label className="subtle">Sheet max height (mm)</label>
                  <input
                    type="number"
                    value={sheetMaxHeightMm}
                    onChange={(e) => setSheetMaxHeightMm(e.target.value)}
                    placeholder="—"
                  />
                </div>
                <div className="col">
                  <label className="subtle">Roll max width (mm)</label>
                  <input
                    type="number"
                    value={rollMaxWidthMm}
                    onChange={(e) => setRollMaxWidthMm(e.target.value)}
                    placeholder="—"
                  />
                </div>
              </div>
            ) : (
              <textarea
                rows={6}
                value={metaJson}
                onChange={(e) => setMetaJson(e.target.value)}
                style={{ fontFamily: "monospace", fontSize: 12, width: "100%" }}
              />
            )}
          </div>

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
                <>
                  <button type="button" onClick={handleToggleActive}>
                    {editing.active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={handleDeleteInModal}
                    disabled={rates.length > 0}
                    title={rates.length > 0 ? "Remove all rates first or deactivate" : "Delete machine"}
                  >
                    Delete
                  </button>
                </>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={closeModal}>Cancel</button>
              <button type="button" className="primary" onClick={saveMachine} disabled={!name.trim()}>
                {editing ? "Save" : "Create"}
              </button>
            </div>
          </div>
        </div>
      </Modal>

      <Modal open={rateModalOpen} title={editingRate ? "Edit Rate" : "Add Rate"} onClose={() => { setRateModalOpen(false); setEditingRate(null); }}>
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
            <button type="button" onClick={() => { setRateModalOpen(false); setEditingRate(null); }}>Cancel</button>
            <button type="button" className="primary" onClick={saveRate} disabled={!rateOperationKey.trim()}>
              {editingRate ? "Save" : "Create"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
