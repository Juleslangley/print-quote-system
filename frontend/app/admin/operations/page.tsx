"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "../../../lib/api";

export default function AdminOperationsPage() {
  const [err, setErr] = useState("");
  const [ops, setOps] = useState<any[]>([]);

  const [code, setCode] = useState("CUT_STRAIGHT");
  const [name, setName] = useState("Cut Straight");
  const [rateType, setRateType] = useState("cut_knife");
  const [calcModel, setCalcModel] = useState("PERIM_M");
  const [paramsJson, setParamsJson] = useState("{}");

  async function load() {
    setErr("");
    try {
      setOps((await api("/api/operations")) || []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createOp() {
    setErr("");
    try {
      const params = JSON.parse(paramsJson);
      await api("/api/operations", {
        method: "POST",
        body: JSON.stringify({ code, name, rate_type: rateType, calc_model: calcModel, params, active: true }),
      });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function toggleActive(op: any) {
    setErr("");
    try {
      await api(`/api/operations/${op.id}`, { method: "PUT", body: JSON.stringify({ active: !op.active }) });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function editOp(op: any) {
    const next = prompt("Edit params JSON:", JSON.stringify(op.params || {}, null, 2));
    if (next === null) return;
    setErr("");
    try {
      const params = JSON.parse(next);
      await api(`/api/operations/${op.id}`, { method: "PUT", body: JSON.stringify({ params }) });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function deleteOp(op: any) {
    if (!confirm(`Delete operation "${op.code}"?`)) return;
    setErr("");
    try {
      await api(`/api/operations/${op.id}`, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <div>
      <p><a href="/admin">← Admin</a></p>
      <h1>Admin · Operations</h1>

      {err && <div style={{ padding: 10, border: "1px solid #c00", marginBottom: 12, whiteSpace: "pre-wrap" }}>{err}</div>}

      <div style={{ border: "1px solid #ddd", padding: 12, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Create operation</h3>
        <div style={{ display: "grid", gap: 8, maxWidth: 600 }}>
          <label>code <input value={code} onChange={(e) => setCode(e.target.value)} /></label>
          <label>name <input value={name} onChange={(e) => setName(e.target.value)} /></label>
          <label>rate_type <input value={rateType} onChange={(e) => setRateType(e.target.value)} /></label>
          <label>calc_model <input value={calcModel} onChange={(e) => setCalcModel(e.target.value)} /></label>
          <label>params (JSON) <textarea value={paramsJson} onChange={(e) => setParamsJson(e.target.value)} rows={4} /></label>
          <button onClick={createOp}>Create</button>
          <button onClick={load}>Refresh</button>
        </div>
      </div>

      <h2>Library ({ops.length})</h2>
      <div style={{ display: "grid", gap: 10 }}>
        {ops.map((op) => (
          <div key={op.id} style={{ border: "1px solid #eee", padding: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div>
                <b>{op.code}</b> — {op.name} {op.active ? "" : <span style={{ color: "#c00" }}>(inactive)</span>}
                <div style={{ fontSize: 13, color: "#555" }}>
                  {op.calc_model} · {op.rate_type}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => toggleActive(op)}>{op.active ? "Deactivate" : "Activate"}</button>
                <button onClick={() => editOp(op)}>Edit params</button>
                <button onClick={() => deleteOp(op)}>Delete</button>
              </div>
            </div>

            <details style={{ marginTop: 6 }}>
              <summary>params</summary>
              <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(op.params || {}, null, 2)}</pre>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
}
