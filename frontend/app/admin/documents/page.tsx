"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";

type DocumentTemplate = {
  id: string;
  doc_type: string;
  name: string;
  active: boolean;
  file_id?: string | null;
  filename?: string | null;
  file_storage_key?: string | null;
  file_mime?: string | null;
  file_size?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

const DOC_TYPES: { key: string; label: string }[] = [
  { key: "purchase_order", label: "Purchase Order" },
  { key: "invoice", label: "Invoice" },
  { key: "quote", label: "Quote" },
  { key: "credit_note", label: "Credit Note" },
  { key: "production_order", label: "Production Order" },
];

function formatBytes(n: number | null | undefined): string {
  const x = typeof n === "number" ? n : 0;
  if (!x) return "—";
  if (x < 1024) return `${x} B`;
  if (x < 1024 * 1024) return `${(x / 1024).toFixed(1)} KB`;
  return `${(x / (1024 * 1024)).toFixed(1)} MB`;
}

export default function AdminDocumentsPage() {
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Record<string, File | null>>({});

  const byType = useMemo(() => {
    const map: Record<string, DocumentTemplate> = {};
    for (const t of templates || []) map[t.doc_type] = t;
    return map;
  }, [templates]);

  async function load() {
    setErr("");
    setLoading(true);
    try {
      const res = await api<DocumentTemplate[]>("/api/document-templates");
      setTemplates(res ?? []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function onPick(docType: string, file: File | null) {
    setSelectedFiles((prev) => ({ ...prev, [docType]: file }));
  }

  async function upload(docType: string) {
    const f = selectedFiles[docType];
    if (!f) return;
    setErr("");
    try {
      const form = new FormData();
      form.append("file", f);
      await api(`/api/document-templates/${docType}/upload`, { method: "POST", body: form });
      onPick(docType, null);
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function remove(docType: string) {
    setErr("");
    try {
      await api(`/api/document-templates/${docType}`, { method: "DELETE" });
      onPick(docType, null);
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function download(docType: string) {
    setErr("");
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const url = `${window.location.origin}/api/document-templates/${docType}/download`;
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then(async (r) => {
        if (!r.ok) throw new Error(await r.text());
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${docType}.pdf`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }

  return (
    <div>
      <p>
        <a href="/admin">← Admin</a>
      </p>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Documents</h1>
          <div className="subtle">Upload PDF templates for documents we generate (PO, invoice, quote, credit note, production order).</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" onClick={load} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#c00", whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {err}
        </div>
      )}

      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 10px" }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "0 10px" }}>Type</th>
                <th style={{ padding: "0 10px" }}>Current template</th>
                <th style={{ padding: "0 10px" }}>Size</th>
                <th style={{ padding: "0 10px" }}>Updated</th>
                <th style={{ padding: "0 10px" }}></th>
              </tr>
            </thead>
            <tbody>
              {DOC_TYPES.map(({ key, label }, index) => {
                const t = byType[key] || null;
                const hasFile = !!t?.file_id;
                const picked = selectedFiles[key] || null;
                return (
                  <tr
                    key={key}
                    style={{
                      background: index % 2 === 0 ? "#ffffff" : "#f8f8f8",
                      border: "1px solid #eee",
                    }}
                  >
                    <td style={{ padding: "12px 10px", borderTopLeftRadius: 12, borderBottomLeftRadius: 12 }}>
                      <div style={{ fontWeight: 700 }}>{label}</div>
                      <div className="subtle">{key}</div>
                    </td>
                    <td style={{ padding: "12px 10px" }}>
                      <div style={{ fontWeight: 600 }}>{hasFile ? (t?.filename || "template.pdf") : "—"}</div>
                      <div className="subtle">{hasFile ? (t?.file_mime || "application/pdf") : "No template uploaded"}</div>
                    </td>
                    <td style={{ padding: "12px 10px" }}>{hasFile ? formatBytes(t?.file_size ?? null) : "—"}</td>
                    <td style={{ padding: "12px 10px" }}>
                      {t?.updated_at ? new Date(t.updated_at).toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "12px 10px", borderTopRightRadius: 12, borderBottomRightRadius: 12 }}>
                      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", flexWrap: "wrap" }}>
                        <input
                          type="file"
                          accept=".pdf,application/pdf"
                          onChange={(e) => onPick(key, e.target.files?.[0] || null)}
                        />
                        <button type="button" className="primary" onClick={() => upload(key)} disabled={!picked}>
                          {hasFile ? "Replace" : "Upload"}
                        </button>
                        <button type="button" onClick={() => download(key)} disabled={!hasFile}>
                          Download
                        </button>
                        <button type="button" onClick={() => remove(key)} disabled={!hasFile}>
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

