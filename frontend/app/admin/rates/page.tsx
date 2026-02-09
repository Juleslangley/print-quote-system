"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "../../../lib/api";

export default function AdminRatesPage() {
  const [err, setErr] = useState("");
  const [rates, setRates] = useState<any[]>([]);

  const [rateType, setRateType] = useState("print_flatbed");
  const [setup, setSetup] = useState(15);
  const [hourly, setHourly] = useState(40);
  const [runSpeedJson, setRunSpeedJson] = useState(`{"sqm_per_hour": 25}`);

  async function load() {
    setErr("");
    try {
      const r = await api("/api/rates");
      setRates(r || []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createRate() {
    setErr("");
    try {
      const run_speed = JSON.parse(runSpeedJson);
      await api("/api/rates", {
        method: "POST",
        body: JSON.stringify({
          rate_type: rateType,
          setup_minutes: setup,
          hourly_cost_gbp: hourly,
          run_speed,
          active: true,
        }),
      });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function toggleActive(r: any) {
    setErr("");
    try {
      await api(`/api/rates/${r.id}`, { method: "PUT", body: JSON.stringify({ active: !r.active }) });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function editRate(r: any) {
    const next = prompt("Edit run_speed JSON only:", JSON.stringify(r.run_speed || {}, null, 2));
    if (next === null) return;
    setErr("");
    try {
      const run_speed = JSON.parse(next);
      await api(`/api/rates/${r.id}`, { method: "PUT", body: JSON.stringify({ run_speed }) });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function deleteRate(r: any) {
    if (!confirm(`Delete rate "${r.rate_type}"?`)) return;
    setErr("");
    try {
      await api(`/api/rates/${r.id}`, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <div>
      <p><a href="/admin">← Admin</a></p>
      <h1>Admin · Rates</h1>

      {err && <div style={{ padding: 10, border: "1px solid #c00", marginBottom: 12, whiteSpace: "pre-wrap" }}>{err}</div>}

      <div style={{ border: "1px solid #ddd", padding: 12, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Create rate</h3>
        <div style={{ display: "grid", gap: 8, maxWidth: 600 }}>
          <label>
            rate_type
            <input value={rateType} onChange={(e) => setRateType(e.target.value)} />
          </label>
          <label>
            setup_minutes
            <input type="number" value={setup} onChange={(e) => setSetup(parseFloat(e.target.value || "0"))} />
          </label>
          <label>
            hourly_cost_gbp
            <input type="number" value={hourly} onChange={(e) => setHourly(parseFloat(e.target.value || "0"))} />
          </label>
          <label>
            run_speed (JSON)
            <textarea value={runSpeedJson} onChange={(e) => setRunSpeedJson(e.target.value)} rows={4} />
          </label>
          <button onClick={createRate}>Create</button>
          <button onClick={load}>Refresh</button>
        </div>
      </div>

      <h2>Rates ({rates.length})</h2>
      <div style={{ display: "grid", gap: 10 }}>
        {rates.map((r) => (
          <div key={r.id} style={{ border: "1px solid #eee", padding: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div>
                <b>{r.rate_type}</b> {r.active ? "" : <span style={{ color: "#c00" }}>(inactive)</span>}
                <div style={{ fontSize: 13, color: "#555" }}>
                  Setup: {r.setup_minutes} min · £{r.hourly_cost_gbp}/hr
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => toggleActive(r)}>{r.active ? "Deactivate" : "Activate"}</button>
                <button onClick={() => editRate(r)}>Edit run_speed</button>
                <button onClick={() => deleteRate(r)}>Delete</button>
              </div>
            </div>

            <details style={{ marginTop: 6 }}>
              <summary>run_speed</summary>
              <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(r.run_speed || {}, null, 2)}</pre>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
}
