"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";

type DocumentTemplate = {
  id: string;
  doc_type: string;
  name: string;
  engine: string;
  content: string;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

const DOC_TYPES: { key: string; label: string }[] = [
  { key: "purchase_order", label: "Purchase Order" },
  { key: "quote", label: "Quote" },
  { key: "invoice", label: "Invoice" },
  { key: "credit_note", label: "Credit Note" },
  { key: "production_order", label: "Production Order" },
];

export default function AdminDocumentsPage() {
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const [docType, setDocType] = useState<string>("purchase_order");
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");

  const selected = useMemo(() => templates.find((t) => t.id === selectedId) || null, [templates, selectedId]);

  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (!selected) {
      setName("");
      setContent("");
      setIsActive(true);
      return;
    }
    setName(selected.name || "");
    setContent(selected.content || "");
    setIsActive(!!selected.is_active);
  }, [selectedId]);

  async function load() {
    setErr("");
    setLoading(true);
    try {
      const res = await api<DocumentTemplate[]>(`/api/document-templates?doc_type=${encodeURIComponent(docType)}`);
      const list = res ?? [];
      setTemplates(list);
      if (!selectedId && list.length) setSelectedId(list[0].id);
      if (selectedId && list.every((t) => t.id !== selectedId)) setSelectedId(list.length ? list[0].id : "");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      setTemplates([]);
      setSelectedId("");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setSelectedId("");
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docType]);

  async function createTemplate() {
    setErr("");
    try {
      const created = await api<DocumentTemplate>("/api/document-templates", {
        method: "POST",
        body: JSON.stringify({
          doc_type: docType,
          name: name || `New ${docType} template`,
          engine: "html_jinja",
          content: content || "",
          is_active: isActive,
        }),
      });
      await load();
      if (created?.id) setSelectedId(created.id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function saveTemplate() {
    if (!selected) return;
    setErr("");
    try {
      await api<DocumentTemplate>(`/api/document-templates/${selected.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name,
          content,
          is_active: isActive,
        }),
      });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function activateTemplate() {
    if (!selected) return;
    setErr("");
    try {
      await api<DocumentTemplate>(`/api/document-templates/${selected.id}/activate`, { method: "POST" });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function deleteTemplate() {
    if (!selected) return;
    if (!confirm(`Delete template "${selected.name || selected.id}"?`)) return;
    setErr("");
    try {
      await api(`/api/document-templates/${selected.id}`, { method: "DELETE" });
      setSelectedId("");
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <div>
      <p>
        <Link href="/admin">← Admin</Link>
      </p>

      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Documents</h1>
          <div className="subtle">Templates only. Editing templates affects future PDFs. PDFs generate automatically when a PO is processed.</div>
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

      <div className="card section" style={{ marginBottom: 12 }}>
        <label className="subtle">Document type</label>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <select value={docType} onChange={(e) => setDocType(e.target.value)} style={{ minWidth: 260 }}>
            {DOC_TYPES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </select>
          <span className="subtle">{templates.length} template(s)</span>
        </div>
      </div>

      <div className="card" style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 14 }}>
        <div style={{ borderRight: "1px solid #eee", paddingRight: 14 }}>
          <div className="subtle" style={{ fontWeight: 700, marginBottom: 8 }}>Templates</div>
          <div style={{ display: "grid", gap: 8 }}>
            {templates.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setSelectedId(t.id)}
                style={{
                  textAlign: "left",
                  padding: "10px 12px",
                  borderRadius: 10,
                  border: "1px solid #e5e5e7",
                  background: t.id === selectedId ? "#f0f0f2" : "#fff",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <div style={{ fontWeight: 700 }}>{t.name || "(unnamed)"}</div>
                  {t.is_active && (
                    <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 999, background: "#d1fae5" }}>
                      active
                    </span>
                  )}
                </div>
                <div className="subtle" style={{ fontSize: 12 }}>{t.id.slice(0, 8)} · {t.engine}</div>
              </button>
            ))}
            {templates.length === 0 && <div className="subtle">No templates yet.</div>}
          </div>
        </div>

        <div>
          <div className="subtle" style={{ fontWeight: 700, marginBottom: 8 }}>
            {selected ? "Edit template" : "Create template"}
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            <div className="row">
              <div className="col">
                <label className="subtle">Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Template name" />
              </div>
              <div className="col">
                <label className="subtle">Active</label>
                <select value={isActive ? "yes" : "no"} onChange={(e) => setIsActive(e.target.value === "yes")}>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </div>
            </div>

            <div>
              <label className="subtle">HTML (Jinja2)</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={22}
                style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace" }}
                placeholder="Paste full HTML template here"
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap" }}>
              {!selected ? (
                <button type="button" className="primary" onClick={createTemplate}>
                  Create
                </button>
              ) : (
                <>
                  <button type="button" onClick={activateTemplate}>Set active</button>
                  <button type="button" className="primary" onClick={saveTemplate}>Save</button>
                  <button type="button" className="danger" onClick={deleteTemplate}>Delete</button>
                </>
              )}
            </div>

            {selected && (
              <div className="subtle" style={{ fontSize: 12 }}>
                Template id: {selected.id}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

