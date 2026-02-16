"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";

type Template = {
  id: string;
  name: string;
  category: string;
  default_material_id: string;
  default_machine_id?: string | null;
  rules: any;
  active: boolean;
};

type Material = { id: string; name: string; type: string; active: boolean };
type Operation = { id: string; code: string; name: string; rate_type: string; calc_model: string; params: any; active: boolean };

type TemplateOpLink = {
  id: string;
  template_id: string;
  operation_id: string;
  sort_order: number;
  params_override: any;
};

type AllowedMaterialLink = { id: string; template_id: string; material_id: string };

export default function AdminTemplatesPage() {
  const [err, setErr] = useState<string>("");

  const [templates, setTemplates] = useState<Template[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [operations, setOperations] = useState<Operation[]>([]);

  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");

  const [templateOpLinks, setTemplateOpLinks] = useState<TemplateOpLink[]>([]);
  const [allowedMaterials, setAllowedMaterials] = useState<AllowedMaterialLink[]>([]);

  const [newOpId, setNewOpId] = useState<string>("");
  const [newOpSort, setNewOpSort] = useState<number>(100);

  const [newAllowedMaterialId, setNewAllowedMaterialId] = useState<string>("");

  const selectedTemplate = useMemo(
    () => templates.find((t) => t.id === selectedTemplateId) || null,
    [templates, selectedTemplateId]
  );

  const materialName = useMemo(() => {
    if (!selectedTemplate) return "";
    const m = materials.find((x) => x.id === selectedTemplate.default_material_id);
    return m ? m.name : "UNKNOWN MATERIAL";
  }, [selectedTemplate, materials]);

  const opById = useMemo(() => {
    const map: Record<string, Operation> = {};
    for (const op of operations) map[op.id] = op;
    return map;
  }, [operations]);

  const allowedMaterialIdSet = useMemo(() => {
    return new Set(allowedMaterials.map((x) => x.material_id));
  }, [allowedMaterials]);

  async function loadBase() {
    setErr("");
    try {
      const [t, m, o] = await Promise.all([
        api<Template[]>("/api/templates"),
        api<any[]>("/api/materials"),
        api<any[]>("/api/operations"),
      ]);
      const tList = (t ?? []) as Template[];
      const mList = (m ?? []) as any[];
      const oList = (o ?? []) as any[];
      setTemplates(tList);
      setMaterials(mList);
      setOperations(oList);
      if (!selectedTemplateId && tList.length) setSelectedTemplateId(tList[0].id);
      if (!newOpId && oList.length) setNewOpId(oList[0].id);
      if (!newAllowedMaterialId && mList.length) setNewAllowedMaterialId(mList[0].id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function loadTemplateDetails(templateId: string) {
    if (!templateId) return;
    setErr("");
    try {
      const [links, allowed] = await Promise.all([
        api<any[]>(`/api/templates/${templateId}/operations`),
        api<any[]>(`/api/templates/${templateId}/allowed-materials`),
      ]);
      const linksList = links || [];
      const sorted = linksList.slice().sort((a: any, b: any) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
      setTemplateOpLinks(sorted);
      setAllowedMaterials(allowed || []);
      if (!newOpId && operations.length) setNewOpId(operations[0].id);
      if (!newAllowedMaterialId && materials.length) setNewAllowedMaterialId(materials[0].id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      setTemplateOpLinks([]);
      setAllowedMaterials([]);
    }
  }

  useEffect(() => {
    loadBase();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("template");
    if (t) setSelectedTemplateId(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedTemplateId) loadTemplateDetails(selectedTemplateId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTemplateId]);

  async function addOperationLink() {
    if (!selectedTemplateId) return;
    setErr("");
    try {
      await api(`/api/templates/${selectedTemplateId}/operations`, {
        method: "POST",
        body: JSON.stringify({
          operation_id: newOpId,
          sort_order: Number.isFinite(newOpSort) ? newOpSort : 100,
          params_override: {},
        }),
      });
      await loadTemplateDetails(selectedTemplateId);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function removeOperationLink(linkId: string) {
    if (!selectedTemplateId) return;
    setErr("");
    try {
      await api(`/api/template-operations/${linkId}`, { method: "DELETE" });
      await loadTemplateDetails(selectedTemplateId);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function editParamsOverride(link: TemplateOpLink) {
    const current = JSON.stringify(link.params_override || {}, null, 2);
    const next = prompt("Edit params_override JSON:", current);
    if (next === null) return;
    setErr("");
    try {
      const parsed = next.trim() ? JSON.parse(next) : {};
      await api(`/api/template-operations/${link.id}`, {
        method: "PUT",
        body: JSON.stringify({ params_override: parsed }),
      });
      await loadTemplateDetails(selectedTemplateId!);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function reorderLinks(newLinks: TemplateOpLink[]) {
    if (!selectedTemplateId) return;
    setErr("");
    try {
      await api(`/api/templates/${selectedTemplateId}/operations/reorder`, {
        method: "POST",
        body: JSON.stringify({
          items: newLinks.map((l) => ({ link_id: l.id, sort_order: l.sort_order })),
        }),
      });
      setTemplateOpLinks(newLinks.slice().sort((a, b) => a.sort_order - b.sort_order));
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function moveUp(index: number) {
    if (index <= 0) return;
    const arr = templateOpLinks.slice().sort((a, b) => a.sort_order - b.sort_order);
    [arr[index - 1], arr[index]] = [arr[index], arr[index - 1]];
    arr.forEach((l, i) => {
      l.sort_order = i;
    });
    reorderLinks(arr);
  }

  function moveDown(index: number) {
    if (index >= templateOpLinks.length - 1) return;
    const arr = templateOpLinks.slice().sort((a, b) => a.sort_order - b.sort_order);
    [arr[index], arr[index + 1]] = [arr[index + 1], arr[index]];
    arr.forEach((l, i) => {
      l.sort_order = i;
    });
    reorderLinks(arr);
  }

  async function addAllowedMaterial() {
    if (!selectedTemplateId || !newAllowedMaterialId) return;
    setErr("");
    try {
      await api(`/api/templates/${selectedTemplateId}/allowed-materials`, {
        method: "POST",
        body: JSON.stringify({ material_id: newAllowedMaterialId }),
      });
      await loadTemplateDetails(selectedTemplateId);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function removeAllowedMaterial(linkId: string) {
    if (!selectedTemplateId) return;
    setErr("");
    try {
      await api(`/api/template-allowed-materials/${linkId}`, { method: "DELETE" });
      await loadTemplateDetails(selectedTemplateId);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  const sortedLinks = useMemo(
    () => templateOpLinks.slice().sort((a, b) => a.sort_order - b.sort_order),
    [templateOpLinks]
  );

  return (
    <div>
      <p><Link href="/admin">← Admin</Link></p>
      <h1>Templates + operation order</h1>

      {err && (
        <div style={{ padding: 10, border: "1px solid #c00", marginBottom: 12, whiteSpace: "pre-wrap" }}>
          {err}
        </div>
      )}

      <label style={{ display: "block", marginBottom: 12 }}>
        Template{" "}
        <select
          value={selectedTemplateId}
          onChange={(e) => setSelectedTemplateId(e.target.value)}
          style={{ minWidth: 260 }}
        >
          {templates.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
      </label>

      {selectedTemplate && (
        <>
          <p><b>{selectedTemplate.name}</b> — default material: {materialName}</p>

          <h2>Operation order (finish blocks)</h2>
          <ul style={{ listStyle: "none", paddingLeft: 0 }}>
            {sortedLinks.map((link, index) => {
              const op = opById[link.operation_id];
              return (
                <li key={link.id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ minWidth: 24 }}>{link.sort_order}</span>
                  <span>{op ? `${op.code} – ${op.name}` : link.operation_id}</span>
                  <button type="button" onClick={() => moveUp(index)} disabled={index === 0}>Up</button>
                  <button type="button" onClick={() => moveDown(index)} disabled={index === sortedLinks.length - 1}>Down</button>
                  <button type="button" onClick={() => editParamsOverride(link)}>Edit params</button>
                  <button type="button" onClick={() => removeOperationLink(link.id)}>Remove</button>
                </li>
              );
            })}
          </ul>

          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 24 }}>
            <select value={newOpId} onChange={(e) => setNewOpId(e.target.value)}>
              {operations.map((o) => (
                <option key={o.id} value={o.id}>{o.code} – {o.name}</option>
              ))}
            </select>
            <input
              type="number"
              value={newOpSort}
              onChange={(e) => setNewOpSort(parseInt(e.target.value || "100", 10))}
              style={{ width: 64 }}
            />
            <button type="button" onClick={addOperationLink}>Add operation</button>
          </div>

          <h2>Allowed materials</h2>
          <ul>
            {allowedMaterials.map((am) => {
              const mat = materials.find((m) => m.id === am.material_id);
              return (
                <li key={am.id} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {mat ? mat.name : am.material_id}
                  <button type="button" onClick={() => removeAllowedMaterial(am.id)}>Remove</button>
                </li>
              );
            })}
          </ul>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
            <select value={newAllowedMaterialId} onChange={(e) => setNewAllowedMaterialId(e.target.value)}>
              {materials.filter((m) => !allowedMaterialIdSet.has(m.id)).map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
            <button type="button" onClick={addAllowedMaterial}>Add material</button>
          </div>
        </>
      )}
    </div>
  );
}
