"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "../../lib/api";

type StoreJob = { id: string; batch_id: string; store_name: string; status: string; box_count?: number };

export default function PackingPackerListPage() {
  const [jobs, setJobs] = useState<StoreJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "pending" | "packed" | "dispatched">("pending");

  useEffect(() => {
    const q = filter === "all" ? "" : `?status=${filter}`;
    api<StoreJob[]>(`/api/packing/store-jobs${q}`)
      .then((data) => setJobs(data ?? []))
      .catch((e) => setErr(e instanceof ApiError ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div style={{ maxWidth: 480, margin: "0 auto", padding: 16, minHeight: "100vh" }}>
      <h1 style={{ fontSize: "1.25rem" }}>Packing — Store jobs</h1>
      <p style={{ fontSize: 14, color: "#666" }}>Tap a store to pack and add photos.</p>

      <div style={{ marginBottom: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {(["pending", "packed", "dispatched", "all"] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setFilter(s)}
            style={{
              padding: "8px 12px",
              background: filter === s ? "#0066cc" : "#eee",
              color: filter === s ? "#fff" : "#333",
              border: "none",
              borderRadius: 6,
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {err && <p style={{ color: "#c00", marginBottom: 12 }}>{err}</p>}
      {loading && <p>Loading…</p>}

      <ul style={{ listStyle: "none", padding: 0 }}>
        {jobs.map((j) => (
          <li key={j.id} style={{ marginBottom: 8 }}>
            <Link
              href={`/packing/jobs/${j.id}`}
              style={{
                display: "block",
                padding: 16,
                background: "#f8f8f8",
                borderRadius: 8,
                color: "#333",
                textDecoration: "none",
              }}
            >
              <span style={{ fontWeight: 600 }}>{j.store_name}</span>
              <span style={{ marginLeft: 8, color: "#666", fontSize: 14 }}>{j.status}</span>
              {j.box_count != null && <span style={{ marginLeft: 8, fontSize: 14 }}>· {j.box_count} boxes</span>}
            </Link>
          </li>
        ))}
      </ul>
      {!loading && jobs.length === 0 && <p style={{ color: "#666" }}>No store jobs.</p>}

      <p style={{ marginTop: 24, fontSize: 14 }}>
        <Link href="/admin/packing" style={{ color: "#0066cc" }}>Admin: Packing Proof</Link>
      </p>
    </div>
  );
}
