"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import Modal from "./Modal";

export type PO = {
  id: string;
  po_number: string | null;
  supplier_id: string;
  status: string;
  order_date: string | null;
  total_gbp: number;
};

type PurchaseOrderListProps = {
  /** When true, navigating to detail adds ?from=materials so Back returns to materials PO tab */
  fromMaterials?: boolean;
  /** Optional header title (when not set, no header row is rendered) */
  title?: string;
  /** Optional header subtitle */
  subtitle?: string;
};

export default function PurchaseOrderList({
  fromMaterials = false,
  title,
  subtitle,
}: PurchaseOrderListProps) {
  const router = useRouter();
  const [err, setErr] = useState("");
  const [list, setList] = useState<PO[]>([]);
  const [suppliers, setSuppliers] = useState<{ id: string; name: string }[]>([]);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [newPOModalOpen, setNewPOModalOpen] = useState(false);
  const [newPOSupplierId, setNewPOSupplierId] = useState("");

  async function load() {
    setErr("");
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      if (statusFilter) params.set("status", statusFilter);
      const path = `/api/purchase-orders${params.toString() ? `?${params}` : ""}`;
      const data = await api.get<PO[]>(path);
      setList(data ?? []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function loadSuppliers() {
    try {
      const list = (await api.get<{ id: string; name: string }[]>("/api/suppliers")) ?? [];
      setSuppliers(list);
      if (list.length && !newPOSupplierId) setNewPOSupplierId(list[0].id);
    } catch {}
  }

  useEffect(() => {
    load();
    loadSuppliers();
  }, [q, statusFilter]);

  const supplierNames: Record<string, string> = useMemo(() => {
    const m: Record<string, string> = {};
    suppliers.forEach((s) => {
      m[s.id] = s.name;
    });
    return m;
  }, [suppliers]);

  function detailHref(poId: string): string {
    const base = `/admin/purchase-orders/${poId}`;
    return fromMaterials ? `${base}?from=materials` : base;
  }

  function openDetail(poId: string) {
    router.push(detailHref(poId));
  }

  async function createNewPO() {
    if (!newPOSupplierId) {
      setErr("Select a supplier");
      return;
    }
    setErr("");
    try {
      const po = await api.post<PO>("/api/purchase-orders", { supplier_id: newPOSupplierId });
      setNewPOModalOpen(false);
      openDetail(po.id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function isDraft(po: PO) {
    return !po.po_number || String(po.po_number).startsWith("DRAFT-");
  }

  async function deleteDraftPO(po: PO, e: React.MouseEvent) {
    e.stopPropagation();
    if (!isDraft(po)) return;
    if (!confirm("Delete this draft permanently? This cannot be undone.")) return;
    setErr("");
    try {
      await api(`/api/purchase-orders/${po.id}`, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function cancelPO(po: PO, e: React.MouseEvent) {
    e.stopPropagation();
    const label = po.po_number && !String(po.po_number).startsWith("DRAFT-") ? po.po_number : "Draft";
    if (!confirm(`Cancel purchase order ${label}?`)) return;
    setErr("");
    try {
      await api(`/api/purchase-orders/${po.id}/status`, {
        method: "POST",
        body: JSON.stringify({ status: "cancelled" }),
      });
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <>
      {title != null && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <div>
            <h1 style={{ margin: 0 }}>{title}</h1>
            {subtitle != null && <div className="subtle">{subtitle}</div>}
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button type="button" onClick={load}>
              Refresh
            </button>
            <button
              type="button"
              className="primary"
              onClick={() => {
                setNewPOModalOpen(true);
                loadSuppliers();
              }}
            >
              New PO
            </button>
          </div>
        </div>
      )}
      {err && (
        <div className="card" style={{ borderColor: "#c00", whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {err}
        </div>
      )}

      <div className="card section">
        <div className="row" style={{ alignItems: "center" }}>
          <div className="col">
            <input
              placeholder="Search PO number or supplier..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="col">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="part_received">Part received</option>
              <option value="received">Received</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 10px" }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "0 10px" }}>PO Number</th>
                <th style={{ padding: "0 10px" }}>Supplier</th>
                <th style={{ padding: "0 10px" }}>Status</th>
                <th style={{ padding: "0 10px" }}>Order date</th>
                <th style={{ padding: "0 10px" }}>Total</th>
                <th style={{ padding: "0 10px" }}></th>
              </tr>
            </thead>
            <tbody>
              {list.map((po, index) => (
                <tr
                  key={po.id}
                  style={{
                    background: hoveredId === po.id ? "#f0f0f2" : index % 2 === 0 ? "#ffffff" : "#f8f8f8",
                    border: "1px solid #eee",
                    cursor: "pointer",
                  }}
                  onMouseEnter={() => setHoveredId(po.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onDoubleClick={() => openDetail(po.id)}
                >
                  <td style={{ padding: "12px 10px", borderTopLeftRadius: 12, borderBottomLeftRadius: 12 }}>
                    <span style={{ fontWeight: 600 }}>{!po.po_number || String(po.po_number).startsWith("DRAFT-") ? "Draft" : po.po_number}</span>
                  </td>
                  <td style={{ padding: "12px 10px" }}>{supplierNames[po.supplier_id] || po.supplier_id}</td>
                  <td style={{ padding: "12px 10px" }}>
                    <span
                      style={{
                        padding: "4px 10px",
                        borderRadius: 999,
                        fontSize: 12,
                        background:
                          po.status === "draft" ? "#f0f0f2" : po.status === "received" ? "#d1fae5" : "#fef3c7",
                        color: "#1d1d1f",
                      }}
                    >
                      {po.status}
                    </span>
                  </td>
                  <td style={{ padding: "12px 10px" }} className="subtle">
                    {po.order_date ? new Date(po.order_date).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "12px 10px" }}>£{po.total_gbp?.toFixed(2) ?? "0.00"}</td>
                  <td style={{ padding: "12px 10px", borderTopRightRadius: 12, borderBottomRightRadius: 12 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "flex-end" }}>
                      <button type="button" onClick={() => openDetail(po.id)}>
                        Open
                      </button>
                      {isDraft(po) && (
                        <button
                          type="button"
                          onClick={(e) => deleteDraftPO(po, e)}
                          title="Delete draft permanently"
                          style={{ padding: "4px 6px", lineHeight: 1 }}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></svg>
                        </button>
                      )}
                      {!isDraft(po) && po.status !== "cancelled" && (
                        <button
                          type="button"
                          onClick={(e) => cancelPO(po, e)}
                          title="Cancel purchase order"
                          style={{ padding: "4px 6px", lineHeight: 1 }}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M18 6L6 18M6 6l12 12" /></svg>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {list.length === 0 && (
          <div className="subtle" style={{ marginTop: 10 }}>
            No purchase orders found.
          </div>
        )}
      </div>

      <Modal open={newPOModalOpen} title="New purchase order" onClose={() => setNewPOModalOpen(false)}>
        <div style={{ display: "grid", gap: 12 }}>
          <div>
            <label className="subtle">Supplier</label>
            <select
              value={newPOSupplierId}
              onChange={(e) => setNewPOSupplierId(e.target.value)}
              style={{ width: "100%", marginTop: 4 }}
            >
              <option value="">Select supplier</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          {err && newPOModalOpen && <div style={{ color: "#c00", fontSize: 14 }}>{err}</div>}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" onClick={() => setNewPOModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="primary" onClick={createNewPO} disabled={!newPOSupplierId}>
              Create
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
