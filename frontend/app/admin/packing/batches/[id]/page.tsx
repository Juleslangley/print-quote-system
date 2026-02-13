"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

type StoreJob = { id: string; batch_id: string; store_name: string; status: string; box_count?: number; notes?: string };

export default function PackingBatchDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const [storeJobs, setStoreJobs] = useState<StoreJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api<StoreJob[]>(`/api/packing/store-jobs?batch_id=${id}`)
      .then((data) => setStoreJobs(data ?? []))
      .catch((e) => setErr(e instanceof ApiError ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  if (!id) return null;
  if (loading) return <p>Loading…</p>;

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 24 }}>
      <p><Link href="/admin/packing" style={{ color: "#0066cc" }}>← Packing Proof</Link></p>
      <h1>Batch {id.slice(0, 8)}</h1>
      {err && <p style={{ color: "#c00" }}>{err}</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {storeJobs.map((sj) => (
          <li key={sj.id} style={{ marginBottom: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
            <Link href={`/packing/jobs/${sj.id}`} style={{ color: "#0066cc", fontWeight: 600 }}>
              {sj.store_name}
            </Link>
            <span style={{ marginLeft: 8, color: "#666" }}>{sj.status}</span>
            {sj.box_count != null && <span style={{ marginLeft: 8 }}>Boxes: {sj.box_count}</span>}
          </li>
        ))}
      </ul>
      {storeJobs.length === 0 && <p style={{ color: "#666" }}>No store jobs in this batch. Upload an allocation file.</p>}
    </div>
  );
}
