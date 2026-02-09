"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "../../../lib/api";

export default function AdminMarginsPage() {
  const [err, setErr] = useState("");
  const [profiles, setProfiles] = useState<any[]>([]);

  const [name, setName] = useState("Standard Trade");
  const [target, setTarget] = useState(0.40);
  const [minMargin, setMinMargin] = useState(0.25);
  const [minSell, setMinSell] = useState(15.0);
  const [roundingJson, setRoundingJson] = useState(`{"mode":"NEAREST","step":0.05}`);

  async function load() {
    setErr("");
    try {
      setProfiles((await api("/api/margin-profiles")) || []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createProfile() {
    setErr("");
    try {
      const rounding = JSON.parse(roundingJson);
      await api("/api/margin-profiles", {
        method: "POST",
        body: JSON.stringify({
          name,
          target_margin_pct: target,
          min_margin_pct: minMargin,
          min_sell_gbp: minSell,
          rounding,
          active: true,
        }),
      });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function toggleActive(p: any) {
    setErr("");
    try {
      await api(`/api/margin-profiles/${p.id}`, { method: "PUT", body: JSON.stringify({ active: !p.active }) });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function editProfile(p: any) {
    const next = prompt("Edit profile JSON (safe):", JSON.stringify(p, null, 2));
    if (next === null) return;
    setErr("");
    try {
      const parsed = JSON.parse(next);
      const patch: any = {};
      for (const k of ["name", "target_margin_pct", "min_margin_pct", "min_sell_gbp", "rounding", "active"]) {
        if (k in parsed) patch[k] = parsed[k];
      }
      await api(`/api/margin-profiles/${p.id}`, { method: "PUT", body: JSON.stringify(patch) });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function deleteProfile(p: any) {
    if (!confirm(`Delete margin profile "${p.name}"?`)) return;
    setErr("");
    try {
      await api(`/api/margin-profiles/${p.id}`, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <div>
      <p><a href="/admin">← Admin</a></p>
      <h1>Admin · Margin Profiles</h1>

      {err && <div style={{ padding: 10, border: "1px solid #c00", marginBottom: 12, whiteSpace: "pre-wrap" }}>{err}</div>}

      <div style={{ border: "1px solid #ddd", padding: 12, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Create profile</h3>
        <div style={{ display: "grid", gap: 8, maxWidth: 650 }}>
          <label>Name <input value={name} onChange={(e) => setName(e.target.value)} /></label>
          <label>Target margin (0-1) <input type="number" step="0.01" value={target} onChange={(e) => setTarget(parseFloat(e.target.value || "0"))} /></label>
          <label>Min margin (0-1) <input type="number" step="0.01" value={minMargin} onChange={(e) => setMinMargin(parseFloat(e.target.value || "0"))} /></label>
          <label>Min sell (£) <input type="number" step="0.01" value={minSell} onChange={(e) => setMinSell(parseFloat(e.target.value || "0"))} /></label>
          <label>Rounding (JSON) <textarea rows={3} value={roundingJson} onChange={(e) => setRoundingJson(e.target.value)} /></label>
          <button onClick={createProfile}>Create</button>
          <button onClick={load}>Refresh</button>
        </div>
      </div>

      <h2>Profiles ({profiles.length})</h2>
      <div style={{ display: "grid", gap: 10 }}>
        {profiles.map((p) => (
          <div key={p.id} style={{ border: "1px solid #eee", padding: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div>
                <b>{p.name}</b> {p.active ? "" : <span style={{ color: "#c00" }}>(inactive)</span>}
                <div style={{ fontSize: 13, color: "#555" }}>
                  Target: {p.target_margin_pct} · Min: {p.min_margin_pct} · Min sell: £{p.min_sell_gbp}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => toggleActive(p)}>{p.active ? "Deactivate" : "Activate"}</button>
                <button onClick={() => editProfile(p)}>Edit JSON</button>
                <button onClick={() => deleteProfile(p)}>Delete</button>
              </div>
            </div>

            <details style={{ marginTop: 6 }}>
              <summary>rounding</summary>
              <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(p.rounding || {}, null, 2)}</pre>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
}
