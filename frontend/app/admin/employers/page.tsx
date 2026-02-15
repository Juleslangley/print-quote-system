"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import Modal from "../../_components/Modal";

type EmployerRow = any;

export default function AdminEmployersPage() {
  const [err, setErr] = useState("");
  const [items, setItems] = useState<EmployerRow[]>([]);
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [activeOnly, setActiveOnly] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<EmployerRow | null>(null);
  const [name, setName] = useState("");
  const [contactName, setContactName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState("");
  const [notes, setNotes] = useState("");
  const [active, setActive] = useState(true);

  function resetForm() {
    setName("");
    setContactName("");
    setEmail("");
    setPhone("");
    setRole("");
    setNotes("");
    setActive(true);
  }

  function openCreate() {
    setEditing(null);
    resetForm();
    setModalOpen(true);
  }

  function openEdit(item: EmployerRow) {
    setEditing(item);
    setName(item.name || "");
    setContactName(item.contact_name || "");
    setEmail(item.email || "");
    setPhone(item.phone || "");
    setRole(item.role || "");
    setNotes(item.notes || "");
    setActive(!!item.active);
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditing(null);
  }

  async function load() {
    setErr("");
    try {
      const list = await api<any[]>("/api/employers");
      setItems(list ?? []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  const roleOptions = useMemo(() => {
    const values = new Set<string>();
    for (const i of items) {
      const v = String(i.role || "").trim();
      if (v) values.add(v);
    }
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [items]);

  const filtered = useMemo(() => {
    const text = q.trim().toLowerCase();
    return (items || [])
      .filter((i) => {
        if (activeOnly && !i.active) return false;
        if (roleFilter !== "all" && (i.role || "") !== roleFilter) return false;
        if (!text) return true;
        return (
          (i.name || "").toLowerCase().includes(text) ||
          (i.contact_name || "").toLowerCase().includes(text) ||
          (i.email || "").toLowerCase().includes(text) ||
          (i.phone || "").toLowerCase().includes(text) ||
          (i.role || "").toLowerCase().includes(text)
        );
      })
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }, [items, q, roleFilter, activeOnly]);

  async function saveEmployer() {
    setErr("");
    try {
      const payload = {
        name: name.trim(),
        contact_name: contactName.trim(),
        email: email.trim(),
        phone: phone.trim(),
        role: role.trim(),
        notes: notes.trim(),
        active,
      };
      if (!payload.name) {
        setErr("Name is required");
        return;
      }
      if (editing) {
        await api(`/api/employers/${editing.id}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await api("/api/employers", { method: "POST", body: JSON.stringify(payload) });
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
      await api(`/api/employers/${editing.id}`, {
        method: "PUT",
        body: JSON.stringify({ active: !editing.active }),
      });
      setEditing((prev) => (prev ? { ...prev, active: !prev.active } : null));
      await load();
      closeModal();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function handleDelete() {
    if (!editing?.id) return;
    if (!confirm(`Delete employer "${editing.name}"?`)) return;
    setErr("");
    try {
      await api(`/api/employers/${editing.id}`, { method: "DELETE" });
      closeModal();
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Employers</h1>
          <div className="subtle">Manage employer records, contacts, and roles.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" onClick={load}>Refresh</button>
          <button type="button" className="primary" onClick={openCreate}>New Employer</button>
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
            <input placeholder="Search employers..." value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="col">
            <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
              <option value="all">All roles</option>
              {roleOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
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
                <th style={{ padding: "6px 8px" }}>Contact</th>
                <th style={{ padding: "6px 8px" }}>Email</th>
                <th style={{ padding: "6px 8px" }}>Role</th>
                <th style={{ padding: "6px 8px" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, index) => (
                <tr
                  key={item.id}
                  style={{
                    background: hoveredId === item.id ? "#f0f0f2" : index % 2 === 0 ? "#fff" : "#f8f8f8",
                    border: "1px solid #eee",
                    cursor: "pointer",
                  }}
                  onMouseEnter={() => setHoveredId(item.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onDoubleClick={() => openEdit(item)}
                >
                  <td style={{ padding: "8px" }}>
                    {item.name || "-"}
                    {!item.active && <span className="subtle"> (inactive)</span>}
                  </td>
                  <td style={{ padding: "8px" }}>
                    <div>{item.contact_name || "-"}</div>
                    <div className="subtle">{item.phone || ""}</div>
                  </td>
                  <td style={{ padding: "8px" }}>{item.email || "-"}</td>
                  <td style={{ padding: "8px" }}>{item.role || "-"}</td>
                  <td style={{ padding: "8px" }}>
                    <button type="button" onClick={(e) => { e.stopPropagation(); openEdit(item); }}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="subtle" style={{ marginTop: 10 }}>No employers found.</div>
        )}
      </div>

      <Modal open={modalOpen} title={editing ? "Edit Employer" : "New Employer"} onClose={closeModal}>
        <div style={{ display: "grid", gap: 12 }}>
          <div className="row">
            <div className="col">
              <label className="subtle">Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Contact name</label>
              <input value={contactName} onChange={(e) => setContactName(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Role</label>
              <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. HR, Procurement" />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Phone</label>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Notes</label>
              <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            Active
          </label>

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
                  <button type="button" className="danger" onClick={handleDelete}>
                    Delete
                  </button>
                </>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={closeModal}>Cancel</button>
              <button
                type="button"
                className="primary"
                onClick={saveEmployer}
                disabled={!name.trim()}
              >
                {editing ? "Save" : "Create"}
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
