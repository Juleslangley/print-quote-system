"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

type Job = { id: string; job_no: string; title: string; status: string };
type Batch = { id: string; job_id: string; name: string };

export default function AdminPackingPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [createJobTitle, setCreateJobTitle] = useState("");
  const [createBatchJobId, setCreateBatchJobId] = useState("");
  const [createBatchName, setCreateBatchName] = useState("");
  const [uploadBatchId, setUploadBatchId] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    Promise.all([
      api<Job[]>("/api/jobs"),
      api<Batch[]>("/api/packing/batches"),
    ])
      .then(([j, b]) => {
        setJobs(j);
        setBatches(b);
      })
      .catch((e) => setErr(e instanceof ApiError ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleCreateJob = async () => {
    setErr(null);
    try {
      const res = await api<{ id: string; job_no: string }>("/api/jobs", {
        method: "POST",
        body: JSON.stringify({ title: createJobTitle || undefined }),
      });
      setJobs((prev) => [...prev, { id: res.id, job_no: res.job_no, title: createJobTitle, status: "open" }]);
      setCreateJobTitle("");
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  };

  const handleCreateBatch = async () => {
    if (!createBatchJobId) {
      setErr("Select a job");
      return;
    }
    setErr(null);
    try {
      const res = await api<Batch>("/api/packing/batches", {
        method: "POST",
        body: JSON.stringify({ job_id: createBatchJobId, name: createBatchName }),
      });
      setBatches((prev) => [res, ...prev]);
      setCreateBatchJobId("");
      setCreateBatchName("");
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  };

  const handleUploadAllocation = async () => {
    if (!uploadBatchId || !uploadFile) {
      setErr("Select batch and file (CSV or xlsx)");
      return;
    }
    setUploading(true);
    setErr(null);
    try {
      const form = new FormData();
      form.append("file", uploadFile);
      await api(`/api/packing/batches/${uploadBatchId}/upload-allocation`, {
        method: "POST",
        body: form,
      });
      setUploadBatchId("");
      setUploadFile(null);
      if ((document.getElementById("alloc-file") as HTMLInputElement)) {
        (document.getElementById("alloc-file") as HTMLInputElement).value = "";
      }
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <p>Loading…</p>;

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 24 }}>
      <h1>Packing Proof</h1>
      <p style={{ color: "#555" }}>Create jobs, batches, and upload allocation spreadsheets. Packers use the mobile view to complete store jobs.</p>

      {err && <p style={{ color: "#c00", marginBottom: 16 }}>{err}</p>}

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: "1rem" }}>Create job</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder="Title (optional)"
            value={createJobTitle}
            onChange={(e) => setCreateJobTitle(e.target.value)}
            style={{ padding: 8, width: 200 }}
          />
          <button type="button" onClick={handleCreateJob} style={{ padding: "8px 16px" }}>
            Create job
          </button>
        </div>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: "1rem" }}>Create batch (for a job)</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={createBatchJobId}
            onChange={(e) => setCreateBatchJobId(e.target.value)}
            style={{ padding: 8, minWidth: 120 }}
          >
            <option value="">Select job</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>{j.job_no} {j.title ? `– ${j.title}` : ""}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Batch name"
            value={createBatchName}
            onChange={(e) => setCreateBatchName(e.target.value)}
            style={{ padding: 8, width: 180 }}
          />
          <button type="button" onClick={handleCreateBatch} style={{ padding: "8px 16px" }}>
            Create batch
          </button>
        </div>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: "1rem" }}>Upload allocation (CSV / xlsx)</h2>
        <p style={{ fontSize: 13, color: "#666" }}>Columns: store_name (or store), component, description, qty. Rows with qty 0 are skipped.</p>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={uploadBatchId}
            onChange={(e) => setUploadBatchId(e.target.value)}
            style={{ padding: 8, minWidth: 200 }}
          >
            <option value="">Select batch</option>
            {batches.map((b) => (
              <option key={b.id} value={b.id}>{b.name} (job {jobs.find((j) => j.id === b.job_id)?.job_no ?? b.job_id.slice(0, 8)})</option>
            ))}
          </select>
          <input
            id="alloc-file"
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={handleUploadAllocation}
            disabled={uploading || !uploadBatchId || !uploadFile}
            style={{ padding: "8px 16px" }}
          >
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: "1rem" }}>Batches</h2>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {batches.length === 0 && <li style={{ color: "#666" }}>No batches yet.</li>}
          {batches.map((b) => (
            <li key={b.id} style={{ marginBottom: 8 }}>
              <Link href={`/admin/packing/batches/${b.id}`} style={{ color: "#0066cc" }}>
                {b.name || b.id.slice(0, 8)} — job {jobs.find((j) => j.id === b.job_id)?.job_no ?? b.job_id.slice(0, 8)}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <p>
        <Link href="/packing" style={{ color: "#0066cc" }}>Open packer view (mobile-friendly)</Link>
      </p>
    </div>
  );
}
