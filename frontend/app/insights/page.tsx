"use client";

import { useMemo, useState } from "react";

type PlannedInsightsRow = {
  month: string; // YYYY-MM
  materialSpend: number; // currency, planned aggregation
  quotes: number;
  jobs: number;
};

function lastNMonths(n: number): string[] {
  const out: string[] = [];
  const d = new Date();
  d.setDate(1);
  for (let i = 0; i < n; i++) {
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    out.push(`${yyyy}-${mm}`);
    d.setMonth(d.getMonth() - 1);
  }
  return out;
}

function formatCurrency(amount: number): string {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(amount);
  } catch {
    return `$${amount.toFixed(2)}`;
  }
}

export default function InsightsPlanPage() {
  const months = useMemo(() => lastNMonths(6), []);

  // Planned/placeholder data: replace with backend-driven values later.
  const plannedData: PlannedInsightsRow[] = useMemo(() => {
    const seed = [
      { materialSpend: 18340.25, quotes: 62, jobs: 24 },
      { materialSpend: 14210.9, quotes: 51, jobs: 19 },
      { materialSpend: 19680.0, quotes: 73, jobs: 28 },
      { materialSpend: 12105.45, quotes: 44, jobs: 15 },
      { materialSpend: 15888.7, quotes: 58, jobs: 21 },
      { materialSpend: 11002.15, quotes: 39, jobs: 14 },
    ];
    return months.map((m, idx) => ({ month: m, ...seed[idx % seed.length] }));
  }, [months]);

  const [month, setMonth] = useState<string>(months[0] ?? "");
  const row = plannedData.find((r) => r.month === month) ?? plannedData[0];

  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ marginBottom: 6 }}>Insights (Plan)</h1>
          <div className="subtle">Placeholder layout for monthly material spend, quotes, and jobs. No real data wired yet.</div>
        </div>
        <div style={{ minWidth: 220 }}>
          <label className="subtle" style={{ display: "block", marginBottom: 6 }}>
            Month
          </label>
          <select value={month} onChange={(e) => setMonth(e.target.value)}>
            {months.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="section" style={{ marginTop: 16 }}>
        <div className="row">
          <div className="col">
            <div className="card">
              <div className="subtle" style={{ marginBottom: 8 }}>
                Material spend (monthly)
              </div>
              <div style={{ fontSize: 28, fontWeight: 650 }}>{row ? formatCurrency(row.materialSpend) : "—"}</div>
              <div className="subtle" style={{ marginTop: 8 }}>
                Plan: sum of material-related PO lines received/created in the month.
              </div>
            </div>
          </div>
          <div className="col">
            <div className="card">
              <div className="subtle" style={{ marginBottom: 8 }}>
                Quotes (monthly)
              </div>
              <div style={{ fontSize: 28, fontWeight: 650 }}>{row ? row.quotes : "—"}</div>
              <div className="subtle" style={{ marginTop: 8 }}>
                Plan: count of quotes created in the month.
              </div>
            </div>
          </div>
          <div className="col">
            <div className="card">
              <div className="subtle" style={{ marginBottom: 8 }}>
                Jobs (monthly)
              </div>
              <div style={{ fontSize: 28, fontWeight: 650 }}>{row ? row.jobs : "—"}</div>
              <div className="subtle" style={{ marginTop: 8 }}>
                Plan: count of production jobs created (or dispatched) in the month.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="section">
        <div className="card">
          <h2 style={{ fontSize: 16, marginBottom: 8 }}>Monthly trend (planned)</h2>
          <div className="subtle" style={{ marginBottom: 12 }}>
            Plan: a small chart showing the last 6–12 months of spend, quotes, and jobs.
          </div>
          <div
            style={{
              height: 180,
              borderRadius: 14,
              border: "1px dashed #c7c7cc",
              background: "linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,0,0,0.00))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#6e6e73",
              fontSize: 14,
              padding: 16,
              textAlign: "center",
            }}
          >
            Chart placeholder (material spend + quotes + jobs)
          </div>
        </div>
      </div>

      <div className="section">
        <div className="card">
          <h2 style={{ fontSize: 16, marginBottom: 8 }}>Data wiring plan</h2>
          <ul style={{ margin: 0, paddingLeft: 18, color: "#1d1d1f" }}>
            <li style={{ marginBottom: 8 }}>
              <span style={{ fontWeight: 600 }}>Material spend:</span> aggregate by month from purchase orders / supplier invoices (definition to confirm: created vs received vs invoiced).
            </li>
            <li style={{ marginBottom: 8 }}>
              <span style={{ fontWeight: 600 }}>Quotes:</span> count by quote created date (optionally filter by status: draft/sent/accepted).
            </li>
            <li style={{ marginBottom: 8 }}>
              <span style={{ fontWeight: 600 }}>Jobs:</span> count by job created date (optionally also show completed/dispatched counts).
            </li>
          </ul>
          <div className="subtle" style={{ marginTop: 12 }}>
            This page is intentionally “plan only” for now; backend endpoints + exact definitions can be added next.
          </div>
        </div>
      </div>
    </div>
  );
}

