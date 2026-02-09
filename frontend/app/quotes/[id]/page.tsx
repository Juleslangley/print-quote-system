"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "../../../lib/api";

export default function QuoteDetail({ params }: any) {
  const id = params.id as string;

  const [err, setErr] = useState<string>("");
  const [quote, setQuote] = useState<any>(null);
  const [templates, setTemplates] = useState<any[]>([]);
  const [items, setItems] = useState<any[]>([]);

  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [title, setTitle] = useState("Line Item");
  const [qty, setQty] = useState(1);
  const [w, setW] = useState(500);
  const [h, setH] = useState(500);

  const [discountPct, setDiscountPct] = useState(0);

  async function refresh() {
    setErr("");
    try {
      const q = await api(`/api/quotes/${id}`);
      const t = await api("/api/templates");
      const it = await api(`/api/quotes/${id}/items`);
      setQuote(q);
      setTemplates(t);
      setItems(it);
      if (!selectedTemplate && t?.length) setSelectedTemplate(t[0].id);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function addItem() {
    setErr("");
    try {
      await api(`/api/quotes/${id}/items`, {
        method: "POST",
        body: JSON.stringify({
          template_id: selectedTemplate,
          title,
          qty,
          width_mm: w,
          height_mm: h,
          sides: 1,
          options: {},
        }),
      });
      await refresh();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function recalc() {
    setErr("");
    try {
      await api(`/api/quotes/${id}/recalc`, { method: "POST" });
      await refresh();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function applyDiscount() {
    setErr("");
    try {
      await api(`/api/quotes/${id}/commercial`, {
        method: "PUT",
        body: JSON.stringify({ discount_pct: discountPct / 100 }),
      });
      await recalc();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function lockSell(itemId: string, newSell: number) {
    setErr("");
    try {
      await api(`/api/quote-items/${itemId}/commercial`, {
        method: "PUT",
        body: JSON.stringify({
          sell_locked: true,
          manual_sell_total: newSell,
          manual_reason: "Manual lock from UI",
        }),
      });
      await recalc();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  if (!quote) return <div>Loading… {err && <pre>{err}</pre>}</div>;

  return (
    <div>
      <h1>Quote {quote.quote_number}</h1>

      {err && (
        <div style={{ padding: 10, border: "1px solid #c00", marginBottom: 12, whiteSpace: "pre-wrap" }}>
          {err}
        </div>
      )}

      <p>
        <b>Subtotal:</b> £{quote.subtotal_sell?.toFixed?.(2)}{" "}
        | <b>VAT:</b> £{quote.vat?.toFixed?.(2)}{" "}
        | <b>Total:</b> £{quote.total_sell?.toFixed?.(2)}
      </p>

      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14 }}>
        <button onClick={recalc}>Recalc</button>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          Quote discount %
          <input
            type="number"
            value={discountPct}
            onChange={(e) => setDiscountPct(parseFloat(e.target.value || "0"))}
            style={{ width: 90 }}
          />
          <button onClick={applyDiscount}>Apply</button>
        </label>
      </div>

      <h2>Add item</h2>
      <div style={{ display: "grid", gap: 8, maxWidth: 520 }}>
        <label>
          Template
          <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value)}>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>

        <label>
          Qty
          <input type="number" value={qty} onChange={(e) => setQty(parseInt(e.target.value || "1"))} />
        </label>

        <label>
          Width (mm)
          <input type="number" value={w} onChange={(e) => setW(parseFloat(e.target.value || "0"))} />
        </label>

        <label>
          Height (mm)
          <input type="number" value={h} onChange={(e) => setH(parseFloat(e.target.value || "0"))} />
        </label>

        <button onClick={addItem}>Add + Recalc</button>
      </div>

      <h2>Items</h2>
      <div style={{ display: "grid", gap: 12 }}>
        {items.map((it) => (
          <div key={it.id} style={{ border: "1px solid #ddd", padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
              <div>
                <b>{it.title}</b> — {it.qty} × {it.width_mm}×{it.height_mm}mm
                <div>
                  <b>Cost:</b> £{it.cost_total?.toFixed?.(2)}{" "}
                  | <b>Sell:</b> £{it.sell_total?.toFixed?.(2)}{" "}
                  | <b>Margin:</b> {(it.margin_pct * 100)?.toFixed?.(1)}%
                </div>
              </div>

              <button onClick={() => lockSell(it.id, Number(prompt("Lock sell total (£):", String(it.sell_total || 0)) || it.sell_total || 0))}>
                Lock Sell…
              </button>
            </div>

            <details style={{ marginTop: 8 }}>
              <summary>Calc snapshot (engine + policy)</summary>
              <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(it.calc_snapshot, null, 2)}</pre>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
}
