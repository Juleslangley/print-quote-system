"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import {
  DocumentTemplateEditor,
  useDocumentTemplateEditor,
  expandJinjaBlocks,
} from "./DocumentTemplateEditor";

type DocumentTemplate = {
  id: string;
  doc_type: string;
  name: string;
  engine: string;
  content: string;
  template_html?: string | null;
  template_json?: string | null;
  template_css?: string | null;
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
  const [templateHtml, setTemplateHtml] = useState("");
  const [templateJson, setTemplateJson] = useState<string | null>(null);
  const [templateCss, setTemplateCss] = useState("");
  const [isActive, setIsActive] = useState(true);

  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [downloadPdfLoading, setDownloadPdfLoading] = useState(false);
  const [previewPoId, setPreviewPoId] = useState<string>("");
  const [purchaseOrders, setPurchaseOrders] = useState<{ id: number; po_number: string | null }[]>([]);
  const previewFrameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!selected) {
      setName("");
      setContent("");
      setTemplateHtml("");
      setTemplateJson(null);
      setTemplateCss("");
      setIsActive(true);
      return;
    }
    setName(selected.name || "");
    setContent(selected.content || "");
    setTemplateHtml(selected.template_html || "");
    setTemplateJson(selected.template_json ?? null);
    setTemplateCss(selected.template_css || "");
    setIsActive(!!selected.is_active);
  }, [selectedId, selected]);

  const editor = useDocumentTemplateEditor(
    templateHtml || content,
    templateJson,
    docType,
    (html, json) => {
      setTemplateHtml(html);
      setTemplateJson(json);
    }
  );

  // Reset editor content when selected template changes
  useEffect(() => {
    if (!editor) return;
    if (!selected) {
      editor.commands.setContent("");
      return;
    }
    const html = selected.template_html || selected.content;
    const json = selected.template_json;
    try {
      const toSet = json ? JSON.parse(json) : (html || "");
      editor.commands.setContent(toSet || "");
    } catch {
      editor.commands.setContent(html || "");
    }
  }, [editor, selected]);

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

  useEffect(() => {
    if (docType !== "purchase_order") return;
    api<{ id: number; po_number: string | null }[]>("/api/purchase-orders")
      .then((list) => setPurchaseOrders(list ?? []))
      .catch(() => setPurchaseOrders([]));
  }, [docType]);

  async function createTemplate() {
    setErr("");
    try {
      const html = editor ? expandJinjaBlocks(editor.getHTML()) : templateHtml;
      const json = editor ? JSON.stringify(editor.getJSON()) : templateJson;
      const created = await api<DocumentTemplate>("/api/document-templates", {
        method: "POST",
        body: JSON.stringify({
          doc_type: docType,
          name: name || `New ${docType} template`,
          engine: "html_jinja",
          content: content || "",
          template_html: html || "",
          template_json: json,
          template_css: templateCss || "",
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
      const html = editor ? expandJinjaBlocks(editor.getHTML()) : templateHtml;
      const json = editor ? JSON.stringify(editor.getJSON()) : templateJson;
      await api<DocumentTemplate>(`/api/document-templates/${selected.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name,
          content: content || "",
          template_html: html,
          template_json: json,
          template_css: templateCss || "",
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

  function getPreviewBody(): Record<string, unknown> {
    const html = editor ? expandJinjaBlocks(editor.getHTML()) : templateHtml;
    const body: Record<string, unknown> = {
      template_html: html || "",
      template_css: templateCss || "",
      content: content || "",
      doc_type: docType,
    };
    if (docType === "purchase_order" && previewPoId) {
      body.entity_id = previewPoId;
    }
    return body;
  }

  async function previewTemplate() {
    setPreviewLoading(true);
    setErr("");
    try {
      const res = await api<string>("/api/document-templates/preview", {
        method: "POST",
        body: JSON.stringify(getPreviewBody()),
      });
      setPreviewHtml(res);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      setPreviewHtml(null);
    } finally {
      setPreviewLoading(false);
    }
  }

  async function downloadPdf() {
    setDownloadPdfLoading(true);
    setErr("");
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const res = await fetch("/api/document-templates/preview?format=pdf", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(getPreviewBody()),
      });
      if (!res.ok) {
        const text = await res.text();
        let msg = `Download failed (${res.status})`;
        try {
          const j = text ? JSON.parse(text) : null;
          if (j?.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
        } catch {
          if (text) msg = text.slice(0, 300);
        }
        throw new Error(msg);
      }
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      const disposition = res.headers.get("Content-Disposition");
      const match = disposition?.match(/filename="([^"]+)"/);
      a.download = match?.[1] || `${docType}_preview.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
    } catch (e: any) {
      setErr(e?.message || "PDF download failed");
    } finally {
      setDownloadPdfLoading(false);
    }
  }

  useEffect(() => {
    if (previewFrameRef.current && previewHtml) {
      const doc = previewFrameRef.current.contentDocument;
      if (doc) {
        doc.open();
        doc.write(previewHtml);
        doc.close();
      }
    }
  }, [previewHtml]);

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
              <label className="subtle">Template body</label>
              <DocumentTemplateEditor editor={editor} docType={docType} />
            </div>

            <div>
              <label className="subtle">Custom CSS</label>
              <textarea
                value={templateCss}
                onChange={(e) => setTemplateCss(e.target.value)}
                rows={6}
                placeholder="@page { size: A4; } body { font-size: 12px; }"
                style={{ fontFamily: "ui-monospace, monospace", fontSize: 12, width: "100%" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                {docType === "purchase_order" && (
                  <>
                    <label className="subtle" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      Preview with PO:
                      <select
                        value={previewPoId}
                        onChange={(e) => setPreviewPoId(e.target.value)}
                        style={{ minWidth: 180 }}
                      >
                        <option value="">— Mock data —</option>
                        {purchaseOrders.map((po) => (
                          <option key={po.id} value={String(po.id)}>
                            {po.po_number || `PO ${po.id}`}
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                )}
                <button
                  type="button"
                  onClick={previewTemplate}
                  disabled={previewLoading}
                >
                  {previewLoading ? "Loading…" : "Preview"}
                </button>
                <button
                  type="button"
                  onClick={downloadPdf}
                  disabled={downloadPdfLoading}
                >
                  {downloadPdfLoading ? "Generating…" : "Download PDF"}
                </button>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
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
            </div>

            {selected && (
              <div className="subtle" style={{ fontSize: 12 }}>
                Template id: {selected.id}
              </div>
            )}
          </div>
        </div>
      </div>

      {previewHtml && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 style={{ margin: "0 0 12px 0" }}>Preview</h3>
          <iframe
            ref={previewFrameRef}
            title="Template preview"
            style={{
              width: "100%",
              minHeight: 400,
              border: "1px solid #ddd",
              borderRadius: 8,
              background: "#fff",
            }}
          />
          <button
            type="button"
            onClick={() => setPreviewHtml(null)}
            style={{ marginTop: 8 }}
          >
            Close preview
          </button>
        </div>
      )}
    </div>
  );
}
