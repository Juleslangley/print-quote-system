"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "../../../lib/api";

type PO = {
  id: string;
  po_number: string;
  supplier_id: string;
  status: string;
  order_date: string | null;
  total_gbp: number;
};

function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.25)",
        backdropFilter: "blur(10px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        zIndex: 9999,
      }}
      onMouseDown={onClose}
    >
      <div
        style={{
          width: "min(420px, 100%)",
          background: "#fff",
          borderRadius: 20,
          boxShadow: "0 30px 80px rgba(0,0,0,0.2)",
          border: "1px solid #e5e5e7",
          overflow: "hidden",
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div style={{ padding: 18, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between" }}>
          <div style={{ fontWeight: 600 }}>{title}</div>
          <button onClick={onClose}>✕</button>
        </div>
        <div style={{ padding: 18 }}>{children}</div>
      </div>
    </div>
  );
}

export default function AdminPurchaseOrdersPage() {
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
      const data = await api(path);
      setList(data || []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function loadSuppliers() {
    try {
      const data = await api("/api/suppliers");
      setSuppliers(data || []);
      if (data?.length && !newPOSupplierId) setNewPOSupplierId(data[0].id);
    } catch {}
  }

  useEffect(() => {
    load();
    loadSuppliers();
  }, [q, statusFilter]);

  const supplierNames: Record<string, string> = useMemo(() => {
    const m: Record<string, string> = {};
    suppliers.forEach((s) => { m[s.id] = s.name; });
    return m;
  }, [suppliers]);

  async function createNewPO() {
    if (!newPOSupplierId) {
      setErr("Select a supplier");
      return;
    }
    setErr("");
    try {
      const po = await api("/api/purchase-orders", {
        method: "POST",
        body: JSON.stringify({ supplier_id: newPOSupplierId }),
      });
      setNewPOModalOpen(false);
      router.push(`/admin/purchase-orders/${po.id}`);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Purchase Orders</h1>
          <div className="subtle">Create and manage purchase orders to suppliers.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={load}>Refresh</button>
          <button className="primary" onClick={() => { setNewPOModalOpen(true); loadSuppliers(); }}>New PO</button>
        </div>
      </div>

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
                  onDoubleClick={() => router.push(`/admin/purchase-orders/${po.id}`)}
                >
                  <td style={{ padding: "12px 10px", borderTopLeftRadius: 12, borderBottomLeftRadius: 12 }}>
                    <span style={{ fontWeight: 600 }}>{po.po_number}</span>
                  </td>
                  <td style={{ padding: "12px 10px" }}>{supplierNames[po.supplier_id] || po.supplier_id}</td>
                  <td style={{ padding: "12px 10px" }}>
                    <span
                      style={{
                        padding: "4px 10px",
                        borderRadius: 999,
                        fontSize: 12,
                        background: po.status === "draft" ? "#f0f0f2" : po.status === "received" ? "#d1fae5" : "#fef3c7",
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
                    <button onClick={() => router.push(`/admin/purchase-orders/${po.id}`)}>Open</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {list.length === 0 && <div className="subtle" style={{ marginTop: 10 }}>No purchase orders found.</div>}
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
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          {err && newPOModalOpen && <div style={{ color: "#c00", fontSize: 14 }}>{err}</div>}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button onClick={() => setNewPOModalOpen(false)}>Cancel</button>
            <button className="primary" onClick={createNewPO} disabled={!newPOSupplierId}>Create draft</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
