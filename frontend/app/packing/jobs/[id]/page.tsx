"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

type LineItem = { id: string; component: string; description: string; qty: number };
type StoreJobDetail = {
  id: string;
  batch_id: string;
  store_name: string;
  status: string;
  box_count?: number;
  notes?: string;
  packed_at?: string;
  dispatched_at?: string;
  line_items: LineItem[];
};

export default function PackingStoreJobPage() {
  const params = useParams();
  const id = params?.id as string;
  const [job, setJob] = useState<StoreJobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [patchStatus, setPatchStatus] = useState("");
  const [patchBoxCount, setPatchBoxCount] = useState("");
  const [patchNotes, setPatchNotes] = useState("");
  const [patching, setPatching] = useState(false);
  const [photoFiles, setPhotoFiles] = useState<FileList | null>(null);
  const [uploadingPhotos, setUploadingPhotos] = useState(false);

  const load = () => {
    if (!id) return;
    api<StoreJobDetail>(`/api/packing/store-jobs/${id}`)
      .then((data) => setJob(data))
      .catch((e) => setErr(e instanceof ApiError ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [id]);

  const handlePatch = async () => {
    if (!id) return;
    setPatching(true);
    setErr(null);
    const body: { status?: string; box_count?: number; notes?: string } = {};
    if (patchStatus) body.status = patchStatus;
    if (patchBoxCount !== "") body.box_count = parseInt(patchBoxCount, 10);
    if (patchNotes !== "") body.notes = patchNotes;
    if (Object.keys(body).length === 0) {
      setPatching(false);
      return;
    }
    try {
      const updated = await api<StoreJobDetail>(`/api/packing/store-jobs/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setJob(updated);
      setPatchStatus("");
      setPatchBoxCount("");
      setPatchNotes("");
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setPatching(false);
    }
  };

  const handleUploadPhotos = async () => {
    if (!id || !photoFiles?.length) return;
    setUploadingPhotos(true);
    setErr(null);
    try {
      const form = new FormData();
      for (let i = 0; i < photoFiles.length; i++) {
        form.append("files", photoFiles[i]);
      }
      await api(`/api/packing/store-jobs/${id}/photos`, {
        method: "POST",
        body: form,
      });
      setPhotoFiles(null);
      if (document.getElementById("photo-input") as HTMLInputElement) {
        (document.getElementById("photo-input") as HTMLInputElement).value = "";
      }
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setUploadingPhotos(false);
    }
  };

  if (!id) return null;
  if (loading || !job) return <p>Loading…</p>;

  return (
    <div style={{ maxWidth: 480, margin: "0 auto", padding: 16 }}>
      <p><Link href="/packing" style={{ color: "#0066cc" }}>← Store jobs</Link></p>
      <h1 style={{ fontSize: "1.25rem" }}>{job.store_name}</h1>
      <p style={{ color: "#666" }}>Status: {job.status}</p>

      {err && <p style={{ color: "#c00", marginBottom: 12 }}>{err}</p>}

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: "1rem" }}>Line items</h2>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {job.line_items.map((li) => (
            <li key={li.id} style={{ padding: "8px 0", borderBottom: "1px solid #eee" }}>
              <strong>{li.component}</strong> {li.description && `— ${li.description}`} × {li.qty}
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: "1rem" }}>Update</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <select
            value={patchStatus}
            onChange={(e) => setPatchStatus(e.target.value)}
            style={{ padding: 8 }}
          >
            <option value="">— Status —</option>
            <option value="pending">Pending</option>
            <option value="packed">Packed</option>
            <option value="dispatched">Dispatched</option>
          </select>
          <input
            type="number"
            placeholder="Box count"
            value={patchBoxCount}
            onChange={(e) => setPatchBoxCount(e.target.value)}
            style={{ padding: 8 }}
          />
          <input
            type="text"
            placeholder="Notes"
            value={patchNotes}
            onChange={(e) => setPatchNotes(e.target.value)}
            style={{ padding: 8 }}
          />
          <button type="button" onClick={handlePatch} disabled={patching} style={{ padding: "10px 16px" }}>
            {patching ? "Saving…" : "Save"}
          </button>
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: "1rem" }}>Photos</h2>
        <input
          id="photo-input"
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => setPhotoFiles(e.target.files)}
          style={{ marginBottom: 8 }}
        />
        <button
          type="button"
          onClick={handleUploadPhotos}
          disabled={uploadingPhotos || !photoFiles?.length}
          style={{ padding: "8px 16px" }}
        >
          {uploadingPhotos ? "Uploading…" : "Upload photos"}
        </button>
      </section>
    </div>
  );
}
