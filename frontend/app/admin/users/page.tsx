"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import Modal from "../../_components/Modal";

type UserRow = any;

export default function AdminUsersPage() {
  const [err, setErr] = useState("");
  const [items, setItems] = useState<UserRow[]>([]);
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [activeOnly, setActiveOnly] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>("sales");
  const [active, setActive] = useState(true);
  const [password, setPassword] = useState("");
  const [tempPasswordShown, setTempPasswordShown] = useState<string | null>(null);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [menuDeny, setMenuDeny] = useState<string[]>([]);

  const MENU_KEYS: { key: string; label: string }[] = [
    { key: "home", label: "Home" },
    { key: "quotes", label: "Quotes" },
    { key: "admin", label: "Admin" },
    { key: "admin.materials", label: "Materials" },
    { key: "admin.suppliers", label: "Suppliers" },
    { key: "admin.machines", label: "Machines" },
    { key: "admin.customers", label: "Customers" },
    { key: "admin.users", label: "Users" },
    { key: "admin.rates", label: "Rates" },
    { key: "admin.operations", label: "Operations" },
    { key: "admin.templates", label: "Templates" },
    { key: "admin.margins", label: "Margin profiles" },
    { key: "production", label: "Production" },
  ];

  function resetForm() {
    setFullName("");
    setEmail("");
    setRole("sales");
    setActive(true);
    setPassword("");
    setTempPasswordShown(null);
    setShowResetPassword(false);
    setNewPassword("");
    setMenuDeny([]);
  }

  function openCreate() {
    setEditing(null);
    resetForm();
    setModalOpen(true);
  }

  function openEdit(u: UserRow) {
    setEditing(u);
    setFullName(u.full_name ?? "");
    setEmail(u.email ?? "");
    setRole(u.role ?? "sales");
    setActive(!!u.active);
    setPassword("");
    setTempPasswordShown(null);
    setShowResetPassword(false);
    setNewPassword("");
    setMenuDeny(Array.isArray(u.menu_deny) ? [...u.menu_deny] : []);
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditing(null);
    setShowResetPassword(false);
  }

  async function load() {
    setErr("");
    try {
      const list = await api<any[]>("/api/users");
      setItems(list ?? []);
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
      .filter((u) => {
        if (activeOnly && !u.active) return false;
        if (roleFilter !== "all" && u.role !== roleFilter) return false;
        if (!text) return true;
        return (
          (u.email || "").toLowerCase().includes(text) ||
          (u.full_name || "").toLowerCase().includes(text)
        );
      })
      .sort((a, b) => (a.email || "").localeCompare(b.email || ""));
  }, [items, q, roleFilter, activeOnly]);

  async function saveUser() {
    setErr("");
    try {
      if (editing) {
        await api(`/api/users/${editing.id}`, {
          method: "PUT",
          body: JSON.stringify({
            full_name: fullName.trim(),
            role: role.trim() || "sales",
            active,
            menu_deny: menuDeny,
          }),
        });
        closeModal();
      } else {
        if (!email.trim()) {
          setErr("Email is required");
          return;
        }
        const payload: any = {
          email: email.trim().toLowerCase(),
          full_name: fullName.trim(),
          role: role.trim() || "sales",
          active,
        };
        if (password.trim()) payload.password = password;
        const res = await api<{ temp_password?: string }>("/api/users", { method: "POST", body: JSON.stringify(payload) });
        if (res?.temp_password) setTempPasswordShown(res.temp_password);
        else {
          closeModal();
          await load();
        }
      }
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function handleToggleActive() {
    if (!editing?.id) return;
    setErr("");
    try {
      await api(`/api/users/${editing.id}`, {
        method: "PUT",
        body: JSON.stringify({ active: !editing.active }),
      });
      setEditing((prev) => (prev ? { ...prev, active: !prev.active } : null));
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function handleResetPassword() {
    if (!editing?.id || !newPassword.trim()) return;
    setErr("");
    try {
      await api(`/api/users/${editing.id}/password`, {
        method: "PUT",
        body: JSON.stringify({ new_password: newPassword }),
      });
      setShowResetPassword(false);
      setNewPassword("");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function copyTempPassword() {
    if (tempPasswordShown && typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(tempPasswordShown);
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Users</h1>
          <div className="subtle">Manage logins and roles.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" onClick={load}>Refresh</button>
          <button type="button" className="primary" onClick={openCreate}>New User</button>
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
            <input placeholder="Search name or email..." value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="col">
            <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
              <option value="all">All roles</option>
              <option value="admin">Admin</option>
              <option value="sales">Sales</option>
              <option value="production">Production</option>
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
                <th style={{ padding: "6px 8px" }}>Email</th>
                <th style={{ padding: "6px 8px" }}>Role</th>
                <th style={{ padding: "6px 8px" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u, index) => (
                <tr
                  key={u.id}
                  style={{
                    background: hoveredId === u.id ? "#f0f0f2" : index % 2 === 0 ? "#fff" : "#f8f8f8",
                    border: "1px solid #eee",
                    cursor: "pointer",
                  }}
                  onMouseEnter={() => setHoveredId(u.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onDoubleClick={() => openEdit(u)}
                >
                  <td style={{ padding: "8px" }}>
                    {u.full_name || u.email || "-"}
                    {!u.active && <span className="subtle"> (inactive)</span>}
                  </td>
                  <td style={{ padding: "8px" }}>{u.email || "-"}</td>
                  <td style={{ padding: "8px" }}>{u.role || "-"}</td>
                  <td style={{ padding: "8px" }}>
                    <button type="button" onClick={(e) => { e.stopPropagation(); openEdit(u); }}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="subtle" style={{ marginTop: 10 }}>No users found.</div>
        )}
      </div>

      <Modal open={modalOpen} title={editing ? "Edit User" : "New User"} onClose={closeModal}>
        <div style={{ display: "grid", gap: 12 }}>
          <div className="row">
            <div className="col">
              <label className="subtle">Full name</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Email</label>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={!!editing}
                style={editing ? { opacity: 0.8, cursor: "not-allowed" } : undefined}
              />
              {editing && <div className="subtle" style={{ fontSize: 12, marginTop: 4 }}>Email cannot be changed.</div>}
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Role</label>
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="admin">admin</option>
                <option value="sales">sales</option>
                <option value="production">production</option>
              </select>
            </div>
          </div>
          {!editing && (
            <div className="row">
              <div className="col">
                <label className="subtle">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Optional"
                />
                <div className="subtle" style={{ fontSize: 12, marginTop: 4 }}>
                  Leave blank to auto-generate temp password.
                </div>
              </div>
            </div>
          )}
          {tempPasswordShown && (
            <div style={{ padding: 12, background: "#f0f0f2", borderRadius: 10 }}>
              <div className="subtle" style={{ marginBottom: 6 }}>Generated temp password (show once):</div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <code style={{ flex: 1, padding: 8, background: "#fff", borderRadius: 6 }}>{tempPasswordShown}</code>
                <button type="button" onClick={copyTempPassword}>Copy</button>
                <button type="button" className="primary" onClick={async () => { setTempPasswordShown(null); closeModal(); await load(); }}>
                  Done
                </button>
              </div>
            </div>
          )}
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            Active
          </label>

          {editing && (
            <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
              <div className="subtle" style={{ marginBottom: 8, fontWeight: 600 }}>Menu visibility</div>
              <div style={{ fontSize: 12, marginBottom: 8 }}>Hide menu items for this user (deny-list):</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px" }}>
                {MENU_KEYS.map(({ key, label }) => {
                  const hidden = menuDeny.includes(key);
                  return (
                    <label key={key} style={{ display: "flex", gap: 6, alignItems: "center", whiteSpace: "nowrap" }}>
                      <input
                        type="checkbox"
                        checked={hidden}
                        onChange={() => {
                          setMenuDeny((prev) =>
                            prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
                          );
                        }}
                      />
                      <span>Hide “{label}”</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {editing && (
            <>
              {!showResetPassword ? (
                <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
                  <button type="button" onClick={() => setShowResetPassword(true)}>Reset password</button>
                </div>
              ) : (
                <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
                  <label className="subtle">New password</label>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="New password"
                      style={{ flex: 1 }}
                    />
                    <button type="button" onClick={handleResetPassword} disabled={!newPassword.trim()}>
                      Set password
                    </button>
                    <button type="button" onClick={() => { setShowResetPassword(false); setNewPassword(""); }}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </>
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
                </>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={closeModal}>Cancel</button>
              {!tempPasswordShown && (
                <button
                  type="button"
                  className="primary"
                  onClick={saveUser}
                  disabled={!editing && !email.trim()}
                >
                  {editing ? "Save" : "Create"}
                </button>
              )}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
