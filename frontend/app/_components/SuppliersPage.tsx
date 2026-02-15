"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import Modal from "./Modal";

type Supplier = any;

export default function SuppliersPage() {
  const [err, setErr] = useState("");
  const [items, setItems] = useState<Supplier[]>([]);
  const [usageBySupplier, setUsageBySupplier] = useState<Record<string, any>>({});
  const [materialsBySupplier, setMaterialsBySupplier] = useState<Record<string, any[]>>({});

  const [q, setQ] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);
  const [openSupplierId, setOpenSupplierId] = useState<string>("");
  const [hoveredSupplierId, setHoveredSupplierId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Supplier | null>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [website, setWebsite] = useState("");
  const [contactPerson, setContactPerson] = useState("");
  const [accountsEmail, setAccountsEmail] = useState("");
  const [accountRef, setAccountRef] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [postcode, setPostcode] = useState("");
  const [country, setCountry] = useState("");
  const [lead, setLead] = useState<number>(0);
  const [notes, setNotes] = useState("");
  const [active, setActive] = useState(true);

  function resetForm() {
    setName("");
    setEmail("");
    setPhone("");
    setWebsite("");
    setContactPerson("");
    setAccountsEmail("");
    setAccountRef("");
    setAddress("");
    setCity("");
    setPostcode("");
    setCountry("");
    setLead(0);
    setNotes("");
    setActive(true);
  }

  function openCreate() {
    setEditing(null);
    resetForm();
    setModalOpen(true);
  }

  function openEdit(s: Supplier) {
    setEditing(s);
    setName(s.name || "");
    setEmail(s.email || "");
    setPhone(s.phone || "");
    setWebsite(s.website || "");
    setContactPerson(s.contact_person || "");
    setAccountsEmail(s.accounts_email || "");
    setAccountRef(s.account_ref || "");
    setAddress(s.address || "");
    setCity(s.city || "");
    setPostcode(s.postcode || "");
    setCountry(s.country || "");
    setLead(Number(s.lead_time_days_default || 0));
    setNotes(s.notes || "");
    setActive(!!s.active);
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditing(null);
  }

  async function load() {
    setErr("");
    try {
      const list = (await api<any[]>("/api/suppliers")) ?? [];
      setItems(list);

      const params = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
      const open = params.get("open");
      if (open) setOpenSupplierId(open);

      const out: Record<string, any> = {};
      await Promise.all(
        list.map(async (x: any) => {
          try {
            out[x.id] = await api<any>(`/api/suppliers/${x.id}/usage`);
          } catch {
            // optional endpoint
          }
        })
      );
      setUsageBySupplier(out);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function loadSupplierMaterials(supplierId: string) {
    if (materialsBySupplier[supplierId]) return;
    try {
      const mats = await api<any[]>(`/api/suppliers/${supplierId}/materials`);
      setMaterialsBySupplier((prev) => ({ ...prev, [supplierId]: mats ?? [] }));
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  const filtered = useMemo(() => {
    const text = q.trim().toLowerCase();
    return (items || [])
      .filter((s) => {
        if (activeOnly && !s.active) return false;
        if (!text) return true;
        return (
          (s.name || "").toLowerCase().includes(text) ||
          (s.email || "").toLowerCase().includes(text) ||
          (s.phone || "").toLowerCase().includes(text) ||
          (s.contact_person || "").toLowerCase().includes(text) ||
          (s.accounts_email || "").toLowerCase().includes(text) ||
          (s.account_ref || "").toLowerCase().includes(text) ||
          (s.address || "").toLowerCase().includes(text) ||
          (s.city || "").toLowerCase().includes(text) ||
          (s.postcode || "").toLowerCase().includes(text) ||
          (s.country || "").toLowerCase().includes(text)
        );
      })
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }, [items, q, activeOnly]);

  async function saveSupplier() {
    setErr("");
    try {
      const payload = {
        name: name.trim(),
        email,
        phone,
        website,
        contact_person: contactPerson,
        accounts_email: accountsEmail,
        account_ref: accountRef,
        address,
        city,
        postcode,
        country,
        lead_time_days_default: lead,
        notes,
        active,
      };

      if (!payload.name) {
        setErr("Name is required");
        return;
      }

      if (editing) {
        await api(`/api/suppliers/${editing.id}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await api("/api/suppliers", { method: "POST", body: JSON.stringify(payload) });
      }

      closeModal();
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function toggleActive(s: Supplier): Promise<boolean> {
    setErr("");
    try {
      await api(`/api/suppliers/${s.id}`, { method: "PUT", body: JSON.stringify({ active: !s.active }) });
      await load();
      return true;
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      return false;
    }
  }

  async function del(s: Supplier): Promise<boolean> {
    const u = usageBySupplier[s.id];
    const inUse = (u?.materials_count || 0) > 0;

    if (inUse) {
      setErr(`Can't delete: supplier is in use by ${u.materials_count} material(s).`);
      return false;
    }

    if (!confirm(`Delete supplier "${s.name}"?`)) return false;
    setErr("");
    try {
      await api(`/api/suppliers/${s.id}`, { method: "DELETE" });
      await load();
      return true;
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      return false;
    }
  }

  async function handleToggleActiveInModal() {
    if (!editing) return;
    const ok = await toggleActive(editing);
    if (ok) closeModal();
  }

  async function handleDeleteInModal() {
    if (!editing) return;
    const u = usageBySupplier[editing.id];
    const inUse = (u?.materials_count || 0) > 0;
    if (inUse) {
      setErr(`Can't delete: supplier is in use by ${u.materials_count} material(s).`);
      return;
    }
    const deleted = await del(editing);
    if (deleted) closeModal();
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Suppliers</h1>
          <div className="subtle">Manage supplier records used by Materials and templates.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" onClick={load}>Refresh</button>
          <button type="button" className="primary" onClick={openCreate}>New Supplier</button>
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
            <input placeholder="Search suppliers..." value={q} onChange={(e) => setQ(e.target.value)} />
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
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 10px" }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "0 10px" }}>Name</th>
                <th style={{ padding: "0 10px" }}>Contact</th>
                <th style={{ padding: "0 10px" }}>Address</th>
                <th style={{ padding: "0 10px" }}>Account</th>
                <th style={{ padding: "0 10px" }}>Lead</th>
                <th style={{ padding: "0 10px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, index) => (
                <Fragment key={s.id}>
                  <tr
                    style={{
                      background: hoveredSupplierId === s.id ? "#f0f0f2" : index % 2 === 0 ? "#ffffff" : "#f8f8f8",
                      border: "1px solid #eee",
                      cursor: "pointer",
                    }}
                    onMouseEnter={() => setHoveredSupplierId(s.id)}
                    onMouseLeave={() => setHoveredSupplierId(null)}
                    onDoubleClick={() => openEdit(s)}
                  >
                    <td style={{ padding: "12px 10px", borderTopLeftRadius: 12, borderBottomLeftRadius: 12 }}>
                      <div style={{ fontWeight: 600 }}>
                        {s.name} {!s.active && <span className="subtle"> (inactive)</span>}
                      </div>
                      <div className="subtle">{s.website || ""}</div>
                    </td>
                    <td style={{ padding: "12px 10px" }}>
                      <div>{s.contact_person ? `${s.contact_person} · ` : ""}{s.email || "-"}</div>
                      <div className="subtle">{s.phone || ""}{s.accounts_email ? ` · Accounts: ${s.accounts_email}` : ""}</div>
                    </td>
                    <td style={{ padding: "12px 10px" }}>
                      <div className="subtle" style={{ fontSize: 13 }}>
                        {[s.address, s.city, s.postcode, s.country].filter(Boolean).join(", ") || "-"}
                      </div>
                    </td>
                    <td style={{ padding: "12px 10px" }}>
                      <div>{s.account_ref || "-"}</div>
                    </td>
                    <td style={{ padding: "12px 10px" }}>
                      {s.lead_time_days_default ?? 0} days
                    </td>
                    <td style={{ padding: "12px 10px", borderTopRightRadius: 12, borderBottomRightRadius: 12 }}>
                        <div
                          style={{ display: "flex", gap: 8, justifyContent: "flex-end", flexWrap: "wrap", alignItems: "center" }}
                          onDoubleClick={(e) => e.stopPropagation()}
                        >
                          <button
                            type="button"
                            onClick={async () => {
                              const next = openSupplierId === s.id ? "" : s.id;
                              setOpenSupplierId(next);
                              if (next) await loadSupplierMaterials(next);
                            }}
                            onDoubleClick={(e) => e.stopPropagation()}
                          >
                            {openSupplierId === s.id ? "Hide materials" : "Materials"}
                          </button>
                          <button type="button" onClick={() => openEdit(s)} onDoubleClick={(e) => e.stopPropagation()}>
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); del(s); }}
                            title="Delete supplier"
                            style={{ padding: "4px 6px", lineHeight: 1 }}
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></svg>
                          </button>
                        </div>
                      </td>
                    </tr>

                    {openSupplierId === s.id && (
                      <tr>
                        <td colSpan={6} style={{ padding: "0 10px 14px 10px" }}>
                          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12, background: "#fafafa" }}>
                            {!materialsBySupplier[s.id] ? (
                              <div className="subtle">Loading materials…</div>
                            ) : materialsBySupplier[s.id].length === 0 ? (
                              <div className="subtle">No materials linked to this supplier.</div>
                            ) : (
                              <div style={{ display: "grid", gap: 8 }}>
                                {materialsBySupplier[s.id].map((m) => (
                                  <div key={m.id} style={{ background: "white", border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                                      <div>
                                        <b>{m.name}</b> <span className="subtle">({m.type})</span>{" "}
                                        {!m.active && <span className="subtle">· inactive</span>}
                                        <div className="subtle">
                                          {m.type === "sheet"
                                            ? `Sheet: ${m.sheet_width_mm}×${m.sheet_height_mm} · £${m.cost_per_sheet_gbp}/sheet`
                                            : `Roll: ${m.roll_width_mm}mm · £${m.cost_per_lm_gbp}/lm · Min ${m.min_billable_lm}lm`}
                                        </div>
                                      </div>
                                      <div style={{ display: "flex", gap: 8 }}>
                                        <button type="button" onClick={() => (window.location.href = `/materials#${m.id}`)}>
                                          Open
                                        </button>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && <div className="subtle" style={{ marginTop: 10 }}>No suppliers found.</div>}
      </div>

      <Modal
        open={modalOpen}
        title={editing ? `Edit Supplier` : `New Supplier`}
        onClose={closeModal}
        wide
      >
        <form
          style={{ display: "grid", gap: 12 }}
          onSubmit={(e) => {
            e.preventDefault();
            saveSupplier();
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
              This supplier is inactive.
            </div>
          )}

          <div className="row">
            <div className="col">
              <label className="subtle">Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
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
              <label className="subtle">Contact person</label>
              <input value={contactPerson} onChange={(e) => setContactPerson(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Accounts email</label>
              <input type="email" value={accountsEmail} onChange={(e) => setAccountsEmail(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Website</label>
              <input value={website} onChange={(e) => setWebsite(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Account ref</label>
              <input value={accountRef} onChange={(e) => setAccountRef(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Lead time days</label>
              <input type="number" value={lead} onChange={(e) => setLead(parseInt(e.target.value || "0"))} />
            </div>
          </div>

          <div className="row">
            <div className="col" style={{ gridColumn: "1 / -1" }}>
              <label className="subtle">Address</label>
              <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Street, building, unit" />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">City</label>
              <input value={city} onChange={(e) => setCity(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Postcode</label>
              <input value={postcode} onChange={(e) => setPostcode(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Country</label>
              <input value={country} onChange={(e) => setCountry(e.target.value)} />
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

          {editing && (
            <div
              style={{
                border: "1px solid #eee",
                borderRadius: 12,
                padding: 12,
                background: "#fafafa",
              }}
            >
              {usageBySupplier[editing.id] != null ? (
                <div style={{ fontSize: 14 }}>
                  <div>Materials: {usageBySupplier[editing.id].materials_count ?? 0}</div>
                  <div className="subtle">Templates (default): {usageBySupplier[editing.id].templates_default_count ?? 0}</div>
                  <div className="subtle">Templates (allowed): {usageBySupplier[editing.id].templates_allowed_count ?? 0}</div>
                  {(usageBySupplier[editing.id].materials_count || 0) > 0 && (
                    <div className="subtle" style={{ marginTop: 6 }}>In use</div>
                  )}
                </div>
              ) : (
                <div className="subtle" style={{ fontSize: 14 }}>Usage data unavailable.</div>
              )}
            </div>
          )}

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
                    disabled={(usageBySupplier[editing.id]?.materials_count || 0) > 0}
                    title={(usageBySupplier[editing.id]?.materials_count || 0) > 0 ? "Supplier in use" : "Delete supplier"}
                  >
                    Delete Supplier
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
                  saveSupplier();
                }}
              >
                {editing ? "Save changes" : "Create supplier"}
              </button>
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
}
