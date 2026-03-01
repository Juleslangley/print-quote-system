"use client";

import {
  useEffect,
  useState,
  useCallback,
  useMemo,
  useRef,
} from "react";
import { api, ApiError } from "@/lib/api";
import Modal from "@/app/_components/Modal";
import Drawer from "@/app/_components/ui/Drawer";
import Tooltip from "@/app/_components/ui/Tooltip";
import CommandPalette from "@/app/_components/ui/CommandPalette";
import { ToastProvider, useToast } from "@/app/_components/ui/Toast";

const JOB_TYPE_OPTIONS = [
  { value: "LARGE_FORMAT_SHEET", label: "Large Format sheet" },
  { value: "LARGE_FORMAT_ROLL", label: "Large Format Roll" },
  { value: "LITHO_SHEET", label: "Litho sheet" },
  { value: "DIGITAL_SHEET", label: "Digital sheet" },
] as const;

const JOB_TYPE_SHORT: Record<string, string> = {
  LARGE_FORMAT_SHEET: "LF Sheet",
  LARGE_FORMAT_ROLL: "LF Roll",
  LITHO_SHEET: "Litho",
  DIGITAL_SHEET: "Digital",
};

const LANE_LABELS: Record<string, string> = {
  LF_SHEET: "LF Sheet (Nyala)",
  LF_ROLL: "LF Roll (Epson)",
  LITHO_OUTSOURCE: "Litho (Outsource)",
  DIGITAL_SHEET_PRESS: "Digital (Sheet)",
};

const CURRENCY_FMT = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatCurrency(n: number | undefined | null): string {
  if (n == null || Number.isNaN(n)) return "—";
  return CURRENCY_FMT.format(Number(n));
}

function formatWarningDisplay(msg: string): string {
  if (!msg || typeof msg !== "string") return msg;
  const lowered = msg.toLowerCase();
  if (lowered.startsWith("pricing incomplete")) return msg;
  if (lowered.includes("placeholder") || lowered.includes("unknown") || lowered.includes("missing")) {
    return `Pricing incomplete: ${msg}`;
  }
  return msg;
}

type QuotePart = {
  id: string;
  quote_id: string;
  name: string;
  job_type: string;
  material_id: string | null;
  finished_w_mm: number | null;
  finished_h_mm: number | null;
  quantity: number;
  sides: number;
  preferred_sheet_size_id: string | null;
};

type CalcResult = {
  part: any;
  totals: { total_cost: number; total_sell: number };
  totals_by_lane: Record<string, number>;
  input_hash: string;
  pricing_version: string;
  warnings: string[];
};

function QuoteBuilderInner({
  id,
  params,
}: {
  id: string;
  params: { id: string };
}) {
  const toast = useToast();
  const [err, setErr] = useState("");
  const [quote, setQuote] = useState<any>(null);
  const [parts, setParts] = useState<QuotePart[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [materialsByJobType, setMaterialsByJobType] = useState<
    Record<string, any[]>
  >({});
  const [latestSnapshot, setLatestSnapshot] = useState<any>(null);
  const [priceResult, setPriceResult] = useState<any>(null);
  const [priceLoading, setPriceLoading] = useState(false);

  const [selectedPartId, setSelectedPartId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<QuotePart>>({});
  const [editDirty, setEditDirty] = useState(false);
  const [editSubmitting, setEditSubmitting] = useState(false);

  const [addPartModalOpen, setAddPartModalOpen] = useState(false);
  const [partName, setPartName] = useState("");
  const [partJobType, setPartJobType] = useState("LARGE_FORMAT_SHEET");
  const [partMaterialId, setPartMaterialId] = useState("");
  const [partFinishedW, setPartFinishedW] = useState(500);
  const [partFinishedH, setPartFinishedH] = useState(500);
  const [partQty, setPartQty] = useState(1);
  const [partSides, setPartSides] = useState(1);
  const [addPartSubmitting, setAddPartSubmitting] = useState(false);

  const [calcDrawerOpen, setCalcDrawerOpen] = useState(false);
  const [calcPart, setCalcPart] = useState<QuotePart | null>(null);
  const [calcResult, setCalcResult] = useState<CalcResult | null>(null);
  const [calcTab, setCalcTab] = useState<
    "alternatives" | "production" | "warnings"
  >("alternatives");
  const [calcLoading, setCalcLoading] = useState(false);

  const [lockSubmitting, setLockSubmitting] = useState(false);
  const [density, setDensity] = useState<"compact" | "comfortable">("compact");
  const [activeTab, setActiveTab] = useState<"parts" | "pricing">("parts");
  const [editPartModalOpen, setEditPartModalOpen] = useState(false);
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);
  const [partsSearch, setPartsSearch] = useState("");
  const [quoteNameInput, setQuoteNameInput] = useState("");
  const [quoteNameSaving, setQuoteNameSaving] = useState(false);
  const partsListRef = useRef<HTMLDivElement>(null);

  const selectedPart = useMemo(
    () => parts.find((p) => p.id === selectedPartId) ?? null,
    [parts, selectedPartId]
  );
  const customerName =
    customers.find((c) => c.id === quote?.customer_id)?.name ?? "—";

  async function refresh() {
    setErr("");
    try {
      const [q, p, snap] = await Promise.all([
        api<any>(`/api/quotes/${id}`),
        api<QuotePart[]>(`/api/quotes/${id}/parts`),
        api<any>(`/api/quotes/${id}/latest-snapshot`),
      ]);
      setQuote(q);
      setParts(p ?? []);
      setLatestSnapshot(snap);
      setQuoteNameInput(q?.name ?? "");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function loadMaterialsForJobType(jobType: string) {
    if (materialsByJobType[jobType]) return;
    try {
      const m = await api<any[]>(`/api/materials?job_type=${jobType}`);
      setMaterialsByJobType((prev) => ({ ...prev, [jobType]: m ?? [] }));
    } catch {
      setMaterialsByJobType((prev) => ({ ...prev, [jobType]: [] }));
    }
  }

  useEffect(() => {
    refresh();
  }, [id]);

  useEffect(() => {
    (async () => {
      const c = await api<any[]>("/api/customers").catch(() => []);
      setCustomers(c ?? []);
    })();
  }, []);

  useEffect(() => {
    if (addPartModalOpen) {
      const jt = partJobType || quote?.default_job_type || "LARGE_FORMAT_SHEET";
      loadMaterialsForJobType(jt);
    }
  }, [addPartModalOpen, partJobType, quote?.default_job_type]);

  useEffect(() => {
    parts.forEach((p) => loadMaterialsForJobType(p.job_type));
  }, [parts]);

  useEffect(() => {
    if (selectedPart) {
      setEditForm({
        name: selectedPart.name,
        job_type: selectedPart.job_type,
        material_id: selectedPart.material_id,
        finished_w_mm: selectedPart.finished_w_mm,
        finished_h_mm: selectedPart.finished_h_mm,
        quantity: selectedPart.quantity,
        sides: selectedPart.sides,
      });
      setEditDirty(false);
    } else {
      setEditForm({});
      setEditDirty(false);
    }
  }, [selectedPart?.id]);

  const filteredParts = useMemo(() => {
    if (!partsSearch.trim()) return parts;
    const q = partsSearch.toLowerCase();
    return parts.filter((p) => (p.name || "").toLowerCase().includes(q));
  }, [parts, partsSearch]);

  function openAddPart() {
    setPartJobType(quote?.default_job_type || "LARGE_FORMAT_SHEET");
    setPartMaterialId("");
    setPartName("");
    setPartFinishedW(500);
    setPartFinishedH(500);
    setPartQty(1);
    setPartSides(1);
    setAddPartModalOpen(true);
  }

  async function addPart() {
    setErr("");
    setAddPartSubmitting(true);
    try {
      await api(`/api/quotes/${id}/parts`, {
        method: "POST",
        body: JSON.stringify({
          name: partName.trim() || "Part",
          job_type: partJobType,
          material_id: partMaterialId || null,
          finished_w_mm: partFinishedW,
          finished_h_mm: partFinishedH,
          quantity: partQty,
          sides: partSides,
        }),
      });
      setAddPartModalOpen(false);
      await refresh();
      toast("Part added", "success");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setAddPartSubmitting(false);
    }
  }

  async function savePartEdits() {
    if (!selectedPart || !editDirty) return;
    setErr("");
    setEditSubmitting(true);
    const wasPriced = quote?.status === "priced";
    try {
      await api(`/api/quote-parts/${selectedPart.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editForm.name,
          job_type: editForm.job_type,
          material_id: editForm.material_id || null,
          finished_w_mm: editForm.finished_w_mm,
          finished_h_mm: editForm.finished_h_mm,
          quantity: editForm.quantity,
          sides: editForm.sides,
        }),
      });
      await refresh();
      setEditDirty(false);
      setEditPartModalOpen(false);
      toast("Changes saved", "success");
      if (wasPriced) toast("Quote unlocked (Draft)", "warning");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setEditSubmitting(false);
    }
  }

  function discardPartEdits() {
    if (selectedPart) {
      setEditForm({
        name: selectedPart.name,
        job_type: selectedPart.job_type,
        material_id: selectedPart.material_id,
        finished_w_mm: selectedPart.finished_w_mm,
        finished_h_mm: selectedPart.finished_h_mm,
        quantity: selectedPart.quantity,
        sides: selectedPart.sides,
      });
      setEditDirty(false);
    }
    setEditPartModalOpen(false);
  }

  async function deletePart() {
    if (!selectedPart) return;
    setErr("");
    const wasPriced = quote?.status === "priced";
    try {
      await api(`/api/quote-parts/${selectedPart.id}`, { method: "DELETE" });
      setSelectedPartId(null);
      setEditPartModalOpen(false);
      setEditDirty(false);
      await refresh();
      toast("Part deleted", "success");
      if (wasPriced) toast("Quote unlocked (Draft)", "warning");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  function updateEditField<K extends keyof QuotePart>(
    k: K,
    v: QuotePart[K] | null
  ) {
    setEditForm((f) => ({ ...f, [k]: v }));
    setEditDirty(true);
  }

  async function updatePartJobType(part: QuotePart, newJobType: string) {
    setErr("");
    try {
      const mats = await api<any[]>(`/api/materials?job_type=${newJobType}`);
      const list = mats ?? [];
      const stillAllowed =
        part.material_id &&
        list.some((m: any) => m.id === part.material_id);
      await api(`/api/quote-parts/${part.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          job_type: newJobType,
          material_id: stillAllowed ? part.material_id : null,
        }),
      });
      setMaterialsByJobType((prev) => ({ ...prev, [newJobType]: list }));
      await refresh();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function openCalc(p: QuotePart) {
    setCalcPart(p);
    setCalcResult(null);
    setCalcDrawerOpen(true);
    setCalcLoading(true);
    setErr("");
    setCalcTab("alternatives");
    try {
      const res = await api<CalcResult>(
        `/api/quote-parts/${p.id}/calculate`,
        { method: "POST" }
      );
      setCalcResult(res);
    } catch (e: any) {
      const msg = e instanceof ApiError ? e.message : String(e);
      setErr(msg);
      toast(msg, "warning");
    } finally {
      setCalcLoading(false);
    }
  }

  async function useSheetSize(sheetSizeId: string) {
    if (!calcPart) return;
    setErr("");
    const wasPriced = quote?.status === "priced";
    try {
      await api(`/api/quote-parts/${calcPart.id}`, {
        method: "PATCH",
        body: JSON.stringify({ preferred_sheet_size_id: sheetSizeId }),
      });
      const res = await api<CalcResult>(
        `/api/quote-parts/${calcPart.id}/calculate`,
        { method: "POST" }
      );
      setCalcResult(res);
      setCalcPart({ ...calcPart, preferred_sheet_size_id: sheetSizeId });
      await refresh();
      toast("Sheet size updated", "success");
      if (wasPriced) toast("Quote unlocked (Draft)", "warning");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function lockPrice() {
    setErr("");
    setLockSubmitting(true);
    try {
      await api<any>(`/api/quotes/${id}/lock-price`, { method: "POST" });
      await refresh();
      toast("Price locked", "success");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLockSubmitting(false);
    }
  }

  async function fetchPrice() {
    setErr("");
    setPriceLoading(true);
    try {
      const res = await api<any>(`/api/quotes/${id}/price`, { method: "POST" });
      setPriceResult(res);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setPriceLoading(false);
    }
  }

  useEffect(() => {
    if (parts.length > 0) fetchPrice();
    else setPriceResult(null);
  }, [id, parts]);

  const getMaterialsForPart = (part: QuotePart) =>
    materialsByJobType[part.job_type] ?? [];

  const copyInputHash = useCallback(() => {
    const hash = latestSnapshot?.input_hash;
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    toast("Input hash copied");
  }, [latestSnapshot?.input_hash, toast]);

  async function saveQuoteName() {
    const name = quoteNameInput.trim();
    if (name === (quote?.name ?? "")) return;
    setQuoteNameSaving(true);
    try {
      await api(`/api/quotes/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      });
      setQuote((q: any) => (q ? { ...q, name } : q));
      toast("Quote name saved", "success");
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setQuoteNameSaving(false);
    }
  }

  const cmdItems = useMemo(() => {
    const items: { id: string; label: string; subtitle?: string; onSelect: () => void }[] = [
      { id: "add", label: "Add part", onSelect: openAddPart },
      { id: "lock", label: "Lock price", onSelect: lockPrice },
    ];
    if (selectedPart) {
      items.push({
        id: "calc",
        label: "Open calc for selected part",
        subtitle: selectedPart.name || "Part",
        onSelect: () => openCalc(selectedPart),
      });
    }
    parts.forEach((p) => {
      items.push({
        id: `jump-${p.id}`,
        label: `Edit part: ${p.name || "Unnamed"}`,
        onSelect: () => {
          setSelectedPartId(p.id);
          setEditForm({
            name: p.name,
            job_type: p.job_type,
            material_id: p.material_id,
            finished_w_mm: p.finished_w_mm,
            finished_h_mm: p.finished_h_mm,
            quantity: p.quantity,
            sides: p.sides,
          });
          setEditDirty(false);
          setEditPartModalOpen(true);
          setActiveTab("parts");
        },
      });
    });
    if (selectedPart) {
      const mats = getMaterialsForPart(selectedPart);
      mats.slice(0, 5).forEach((m: any) => {
        items.push({
          id: `mat-${m.id}`,
          label: `Set material: ${m.name}`,
          onSelect: async () => {
            const wasPriced = quote?.status === "priced";
            try {
              await api(`/api/quote-parts/${selectedPart.id}`, {
                method: "PATCH",
                body: JSON.stringify({ material_id: m.id }),
              });
              await refresh();
              toast("Material updated", "success");
              if (wasPriced) toast("Quote unlocked (Draft)", "warning");
            } catch (e: any) {
              setErr(e instanceof ApiError ? e.message : String(e));
            }
          },
        });
      });
    }
    return items;
  }, [
    selectedPart,
    parts,
    quote?.status,
    getMaterialsForPart,
    openAddPart,
    lockPrice,
    openCalc,
    refresh,
  ]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdPaletteOpen(true);
      }
      if (e.key === "/" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) {
        e.preventDefault();
        setCmdPaletteOpen(true);
      }
      if (e.key === "a" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        openAddPart();
      }
      if (e.key === "l" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        lockPrice();
      }
      if (e.key === "Escape") setCmdPaletteOpen(false);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  useEffect(() => {
    const el = partsListRef.current;
    if (!el) return;
    const h = (e: KeyboardEvent) => {
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName))
        return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        const idx = filteredParts.findIndex((p) => p.id === selectedPartId);
        if (idx < filteredParts.length - 1)
          setSelectedPartId(filteredParts[idx + 1].id);
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        const idx = filteredParts.findIndex((p) => p.id === selectedPartId);
        if (idx > 0) setSelectedPartId(filteredParts[idx - 1].id);
      }
      if (e.key === "Enter" && selectedPart) {
        e.preventDefault();
        setEditForm({
          name: selectedPart.name,
          job_type: selectedPart.job_type,
          material_id: selectedPart.material_id,
          finished_w_mm: selectedPart.finished_w_mm,
          finished_h_mm: selectedPart.finished_h_mm,
          quantity: selectedPart.quantity,
          sides: selectedPart.sides,
        });
        setEditDirty(false);
        setEditPartModalOpen(true);
      }
    };
    el.tabIndex = 0;
    el.addEventListener("keydown", h);
    return () => el.removeEventListener("keydown", h);
  }, [filteredParts, selectedPartId, selectedPart]);

  if (!quote)
    return (
      <div className="qb-app">
        <div className="qb-container">
          <div style={{ padding: 48, textAlign: "center" }}>
            <div className="qb-skeleton" style={{ height: 24, width: 200, margin: "0 auto 12px" }} />
            <div className="qb-skeleton" style={{ height: 16, width: 140, margin: "0 auto" }} />
          </div>
          {err && (
            <div
              style={{
                padding: 12,
                border: "1px solid #c00",
                marginTop: 12,
                borderRadius: 8,
                color: "#c00",
              }}
            >
              {err}
            </div>
          )}
        </div>
      </div>
    );

  return (
    <div className="qb-app">
      <div className="qb-container">
        {err && (
          <div
            style={{
              padding: 12,
              border: "1px solid #c00",
              marginBottom: 12,
              borderRadius: 8,
              color: "#c00",
              background: "#fff5f5",
            }}
          >
            {err}
          </div>
        )}

        {/* Sticky header */}
        <header className="qb-sticky-header qb-container">
          <div className="qb-header-content">
            <div style={{ flex: "1 1 200px", minWidth: 0 }}>
              <input
                type="text"
                className="qb-quote-name-input"
                value={quoteNameInput}
                onChange={(e) => setQuoteNameInput(e.target.value)}
                onBlur={saveQuoteName}
                placeholder="Quote name"
              />
              <div className="qb-header-meta">
                {customerName}
                {" · "}
                {quote.status === "priced" && latestSnapshot
                  ? `Rev ${latestSnapshot.revision}`
                  : "—"}
                {" · "}
                {quote?.created_at
                  ? new Date(quote.created_at).toLocaleDateString("en-GB", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })
                  : "—"}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <span
                className={`qb-status-badge qb-badge-${quote.status === "priced" ? "priced" : "draft"}`}
              >
                {quote.status === "priced" ? "● PRICED" : "○ DRAFT"}
              </span>
              {quote.status === "priced" && latestSnapshot && (
                <span className="subtle" style={{ fontSize: 12 }}>
                  Revision {latestSnapshot.revision} · Priced{" "}
                  {new Date(latestSnapshot.created_at).toLocaleString()}
                </span>
              )}
              {quote.status === "priced" && latestSnapshot?.input_hash && (
                <Tooltip content="Copy input hash">
                  <button
                    type="button"
                    className="qb-ghost-btn"
                    onClick={copyInputHash}
                    aria-label="Copy input hash"
                  >
                    ⎘
                  </button>
                </Tooltip>
              )}
            </div>

            <button
              type="button"
              className="primary qb-lock-btn"
              onClick={lockPrice}
              disabled={lockSubmitting}
            >
              {lockSubmitting ? "Locking…" : "Lock price"}
            </button>

            <div className="qb-density-group">
              <span className="subtle" style={{ fontSize: 12 }}>Density</span>
              <button
                type="button"
                className={`qb-ghost-btn ${density === "compact" ? "primary" : ""}`}
                onClick={() => setDensity("compact")}
              >
                Compact
              </button>
              <button
                type="button"
                className={`qb-ghost-btn ${density === "comfortable" ? "primary" : ""}`}
                onClick={() => setDensity("comfortable")}
              >
                Comfortable
              </button>
            </div>

            <button
              type="button"
              className="qb-ghost-btn"
              title="More actions"
              aria-label="More actions"
            >
              ⋯
            </button>
          </div>
        </header>

        {/* Mobile tabs */}
        <div
          style={{
            display: "none",
            marginBottom: 16,
            borderBottom: "1px solid #e5e5e7",
          }}
          className="qb-mobile-tabs"
        >
          <style>{`
            @media (max-width: 1024px) {
              .qb-mobile-tabs { display: flex !important; }
              .qb-two-pane > .qb-pane-parts { display: none; }
              .qb-two-pane > .qb-pane-pricing { display: none; }
              .qb-two-pane > .qb-pane-parts.qb-tab-active { display: block !important; }
              .qb-two-pane > .qb-pane-pricing.qb-tab-active { display: block !important; }
            }
            .qb-mobile-tab {
              padding: 10px 16px;
              font-size: 14px;
              background: none;
              border: none;
              border-bottom: 2px solid transparent;
              margin-bottom: -1px;
              cursor: pointer;
              color: #6e6e73;
            }
            .qb-mobile-tab:hover { color: #1d1d1f; }
            .qb-mobile-tab.qb-active { color: #0071e3; border-bottom-color: #0071e3; font-weight: 500; }
          `}</style>
          <button
            type="button"
            className={`qb-mobile-tab ${activeTab === "parts" ? "qb-active" : ""}`}
            onClick={() => setActiveTab("parts")}
          >
            Parts
          </button>
          <button
            type="button"
            className={`qb-mobile-tab ${activeTab === "pricing" ? "qb-active" : ""}`}
            onClick={() => setActiveTab("pricing")}
          >
            Pricing
          </button>
        </div>

        {/* Two-pane layout: Parts (wide) | Totals */}
        <div
          className={`qb-two-pane ${density === "compact" ? "qb-density-compact" : ""}`}
        >
          {/* Parts list (wide) */}
          <div
            className={`qb-pane-parts qb-card ${activeTab === "parts" ? "qb-tab-active" : ""}`}
          >
            <div className="qb-card-header">
              <span>Parts</span>
              <button
                type="button"
                className="primary"
                style={{ padding: "6px 12px", fontSize: 13 }}
                onClick={openAddPart}
              >
                Add part
              </button>
            </div>
            <input
              type="search"
              className="qb-search-input"
              placeholder="Search parts…"
              value={partsSearch}
              onChange={(e) => setPartsSearch(e.target.value)}
            />
            <div
              ref={partsListRef}
              tabIndex={0}
              className="qb-parts-list"
              style={{ maxHeight: 400 }}
            >
              {filteredParts.map((p) => {
                const mat = getMaterialsForPart(p).find(
                  (m: any) => m.id === p.material_id
                );
                const partName = p.name?.trim() || "Unnamed part";
                const materialLabel = mat?.name || "No material selected";
                const sizeStr =
                  p.finished_w_mm != null && p.finished_h_mm != null
                    ? `${p.finished_w_mm}×${p.finished_h_mm} mm`
                    : "Size not set";
                return (
                  <div
                    key={p.id}
                    className={`qb-parts-row ${p.id === selectedPartId ? "qb-selected" : ""}`}
                    onClick={() => {
                      setSelectedPartId(p.id);
                      setEditForm({
                        name: p.name,
                        job_type: p.job_type,
                        material_id: p.material_id,
                        finished_w_mm: p.finished_w_mm,
                        finished_h_mm: p.finished_h_mm,
                        quantity: p.quantity,
                        sides: p.sides,
                      });
                      setEditDirty(false);
                      setEditPartModalOpen(true);
                    }}
                  >
                    <div className="qb-parts-row-main">
                      <div className="qb-parts-row-line1">
                        <span className="qb-parts-name">{partName}</span>
                        <span className="qb-badge qb-badge-job">
                          {JOB_TYPE_SHORT[p.job_type] ?? p.job_type}
                        </span>
                      </div>
                      <div className="qb-parts-row-line2">
                        <span
                          className={`qb-parts-material ${!mat ? "qb-parts-material-empty" : ""}`}
                          title={materialLabel}
                        >
                          {materialLabel}
                        </span>
                        <span className="qb-parts-sep">·</span>
                        <span className="qb-parts-size">{sizeStr}</span>
                        <span className="qb-parts-sep">·</span>
                        <span className="qb-parts-qty-sublabel">Qty {p.quantity}</span>
                      </div>
                    </div>
                    <div className="qb-parts-row-actions" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        className="qb-calc-btn"
                        onClick={() => openCalc(p)}
                      >
                        Calc
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
            {filteredParts.length === 0 && (
              <div
                style={{
                  padding: 32,
                  textAlign: "center",
                  color: "#6e6e73",
                  fontSize: 14,
                }}
              >
                {partsSearch ? "No parts match your search." : "No parts yet."}
                <br />
                <button
                  type="button"
                  className="primary"
                  style={{ marginTop: 12 }}
                  onClick={openAddPart}
                >
                  Add part
                </button>
              </div>
            )}
          </div>

          {/* Pricing panel (Totals, By lane, Warnings) */}
          <div
            className={`qb-pane-pricing ${activeTab === "pricing" ? "qb-tab-active" : ""}`}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <div className="qb-card">
              <div className="qb-card-header">Totals</div>
              <div className="qb-totals-body">
                {priceLoading ? (
                  <div className="qb-skeleton" style={{ height: 32, marginBottom: 8 }} />
                ) : priceResult ? (
                  (() => {
                    const sell = priceResult.totals?.total_sell;
                    const cost = priceResult.totals?.total_cost;
                    const isPriced =
                      sell != null && Number(sell) > 0;
                    return (
                      <>
                        {!isPriced ? (
                          <div className="qb-totals-placeholder">
                            <span className="subtle" style={{ fontStyle: "italic" }}>
                              Not priced yet
                            </span>
                            {(priceResult.warnings?.length ?? 0) > 0 && (
                              <div className="subtle" style={{ marginTop: 4, fontSize: 12 }}>
                                Fix warnings below to calculate
                              </div>
                            )}
                          </div>
                        ) : (
                          <>
                            <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em" }}>
                              {formatCurrency(sell)}
                            </div>
                            <div className="subtle" style={{ marginTop: 2, fontSize: 13 }}>
                              Sell
                            </div>
                            {cost != null && (
                              <div className="subtle qb-totals-cost-line" style={{ marginTop: 12, fontSize: 13 }}>
                                {formatCurrency(cost)} cost
                                · {((sell! - cost) / sell! * 100).toFixed(0)}% margin
                              </div>
                            )}
                            {latestSnapshot && (
                              <div className="subtle" style={{ marginTop: 12, fontSize: 11 }}>
                                Last calculated{" "}
                                {new Date(latestSnapshot.created_at).toLocaleString()}
                              </div>
                            )}
                          </>
                        )}
                      </>
                    );
                  })()
                ) : (
                  <div className="subtle">Add parts to see pricing.</div>
                )}
              </div>
            </div>

            <div className="qb-card">
              <div className="qb-card-header">By lane</div>
              <div className="qb-lane-list">
                {priceLoading ? (
                  <>
                    <div className="qb-skeleton" style={{ height: 20, marginBottom: 8 }} />
                    <div className="qb-skeleton" style={{ height: 20, marginBottom: 8 }} />
                    <div className="qb-skeleton" style={{ height: 20 }} />
                  </>
                ) : priceResult?.totals_by_lane ? (
                  Object.entries(priceResult.totals_by_lane).map(
                    ([lane, tot]) => {
                      const isZero = tot == null || Number(tot) === 0;
                      return (
                        <div
                          key={lane}
                          className={`qb-lane-row ${isZero ? "qb-lane-zero" : ""}`}
                        >
                          <span className="qb-badge qb-badge-lane">
                            {LANE_LABELS[lane] ?? lane}
                          </span>
                          <span className="qb-lane-value">
                            {formatCurrency(tot)}
                          </span>
                        </div>
                      );
                    }
                  )
                ) : (
                  <div className="subtle">—</div>
                )}
              </div>
            </div>

            {priceResult?.warnings?.length > 0 && (
              <div className="qb-card">
                <div className="qb-card-header">Warnings</div>
                <div className="qb-warnings-list">
                  {priceResult.warnings.map((w, i) => (
                    <div key={i} className="qb-warning-callout">
                      <span className="qb-warning-icon" aria-hidden>⚠</span>
                      <span className="qb-warning-text">{formatWarningDisplay(w)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Edit Part Modal */}
        <Modal
          open={editPartModalOpen}
          title={selectedPart ? `Edit: ${selectedPart.name || "Part"}` : "Edit Part"}
          onClose={() => setEditPartModalOpen(false)}
          confirmOnClose={true}
          isDirty={editDirty}
          onSave={savePartEdits}
        >
          {selectedPart && (
            <div>
              <div className="qb-edit-form">
                <label className="qb-form-label">
                  Part name
                  <input type="text" className="qb-input" value={editForm.name ?? ""} onChange={(e) => updateEditField("name", e.target.value)} />
                </label>
                <label className="qb-form-label">
                  Job type <strong>(required)</strong>
                  <select
                    className="qb-input"
                    value={editForm.job_type ?? ""}
                    onChange={(e) => {
                      updateEditField("job_type", e.target.value);
                      loadMaterialsForJobType(e.target.value);
                    }}
                  >
                    {JOB_TYPE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="qb-form-label">
                  Material
                  <select
                    className="qb-input"
                    value={editForm.material_id ?? ""}
                    onChange={(e) =>
                      updateEditField("material_id", e.target.value || null)
                    }
                  >
                    <option value="">— Select —</option>
                    {(materialsByJobType[editForm.job_type ?? ""] ?? []).map(
                      (m: any) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                        </option>
                      )
                    )}
                  </select>
                </label>
                <div className="qb-form-row">
                  <label className="qb-form-label qb-form-label-half">
                    W (mm)
                    <input
                      type="number"
                      className="qb-input"
                      value={editForm.finished_w_mm ?? ""}
                      onChange={(e) =>
                        updateEditField(
                          "finished_w_mm",
                          parseInt(e.target.value || "0") || null
                        )
                      }
                    />
                  </label>
                  <label className="qb-form-label qb-form-label-half">
                    H (mm)
                    <input
                      type="number"
                      className="qb-input"
                      value={editForm.finished_h_mm ?? ""}
                      onChange={(e) =>
                        updateEditField(
                          "finished_h_mm",
                          parseInt(e.target.value || "0") || null
                        )
                      }
                    />
                  </label>
                </div>
                <div className="qb-form-row">
                  <label className="qb-form-label qb-form-label-half">
                    Qty
                    <input
                      type="number"
                      className="qb-input"
                      value={editForm.quantity ?? 1}
                      onChange={(e) =>
                        updateEditField(
                          "quantity",
                          parseInt(e.target.value || "1") || 1
                        )
                      }
                      min={1}
                    />
                  </label>
                  <label className="qb-form-label qb-form-label-half">
                    Sides
                    <select
                      className="qb-input"
                      value={editForm.sides ?? 1}
                      onChange={(e) =>
                        updateEditField("sides", parseInt(e.target.value) || 1)
                      }
                    >
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                    </select>
                  </label>
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginTop: 20,
                  paddingTop: 16,
                  borderTop: "1px solid #e5e5e7",
                }}
              >
                <button
                  type="button"
                  className="danger"
                  onClick={deletePart}
                  style={{ fontSize: 13 }}
                >
                  Delete part
                </button>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    onClick={discardPartEdits}
                    disabled={!editDirty}
                  >
                    Discard
                  </button>
                  <button
                    type="button"
                    className="primary"
                    onClick={savePartEdits}
                    disabled={!editDirty || editSubmitting}
                  >
                    {editSubmitting ? "Saving…" : "Save changes"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </Modal>

        {/* Add Part Modal */}
        <Modal
          open={addPartModalOpen}
          title="New Part"
          onClose={() => setAddPartModalOpen(false)}
          confirmOnClose={false}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <label>
              Part name
              <input
                type="text"
                value={partName}
                onChange={(e) => setPartName(e.target.value)}
                placeholder="e.g. A4 Flyer"
                style={{ display: "block", width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            <label>
              Job type <strong>(required)</strong>
              <select
                value={partJobType}
                onChange={(e) => {
                  setPartJobType(e.target.value);
                  setPartMaterialId("");
                }}
                style={{ display: "block", width: "100%", padding: 8, marginTop: 4 }}
              >
                {JOB_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Material
              <select
                value={partMaterialId}
                onChange={(e) => setPartMaterialId(e.target.value)}
                style={{ display: "block", width: "100%", padding: 8, marginTop: 4 }}
              >
                <option value="">— Select —</option>
                {(materialsByJobType[partJobType] ?? []).map((m: any) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Finished size (mm)
              <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                <input
                  type="number"
                  value={partFinishedW}
                  onChange={(e) =>
                    setPartFinishedW(parseInt(e.target.value || "0") || 0)
                  }
                  placeholder="W"
                  style={{ flex: 1, padding: 8 }}
                />
                ×
                <input
                  type="number"
                  value={partFinishedH}
                  onChange={(e) =>
                    setPartFinishedH(parseInt(e.target.value || "0") || 0)
                  }
                  placeholder="H"
                  style={{ flex: 1, padding: 8 }}
                />
              </div>
            </label>
            <label>
              Qty
              <input
                type="number"
                value={partQty}
                onChange={(e) =>
                  setPartQty(parseInt(e.target.value || "1") || 1)
                }
                min={1}
                style={{ display: "block", width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            <label>
              Sides
              <select
                value={partSides}
                onChange={(e) =>
                  setPartSides(parseInt(e.target.value) || 1)
                }
                style={{ display: "block", width: "100%", padding: 8, marginTop: 4 }}
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
              </select>
            </label>
            <div
              style={{
                display: "flex",
                gap: 8,
                justifyContent: "flex-end",
                marginTop: 8,
              }}
            >
              <button
                type="button"
                onClick={() => setAddPartModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={addPart}
                disabled={addPartSubmitting}
                className="primary"
              >
                {addPartSubmitting ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </Modal>

        {/* Calc Drawer */}
        <Drawer
          open={calcDrawerOpen}
          onClose={() => setCalcDrawerOpen(false)}
          title={
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>{calcPart?.name || "Part"}</div>
              {calcResult?.part?.sell_price != null && (
                <div className="subtle" style={{ marginTop: 2, fontSize: 13 }}>
                  £{calcResult.part.sell_price.toFixed(2)} sell
                </div>
              )}
            </div>
          }
          width={480}
        >
          {calcLoading ? (
            <div style={{ padding: 24 }}>
              <div className="qb-skeleton" style={{ height: 24, marginBottom: 12 }} />
              <div className="qb-skeleton" style={{ height: 60, marginBottom: 12 }} />
              <div className="qb-skeleton" style={{ height: 80 }} />
            </div>
          ) : calcResult?.part ? (
            <>
              {/* Section 1: Production Overview */}
              <div className="qb-calc-section">
                <div className="qb-calc-section-title">Production overview</div>
                <div className="qb-calc-grid">
                  <span className="qb-calc-label">Machine</span>
                  <span className="qb-calc-value">
                    {calcResult.part.production?.machine_name ??
                      calcResult.part.production?.machine_key ??
                      calcResult.part.routing?.machine_key ??
                      "—"}
                  </span>
                  <span className="qb-calc-label">Lane</span>
                  <span className="qb-calc-value">
                    {calcResult.part.production?.lane ?? calcResult.part.routing?.lane ?? "—"}
                  </span>
                  <span className="qb-calc-label">Selected sheet</span>
                  <span className="qb-calc-value">
                    {calcResult.part.selected_sheet
                      ? `${calcResult.part.selected_sheet.width_mm}×${calcResult.part.selected_sheet.height_mm} mm`
                      : calcResult.part.production?.quantities?.printed_area_sqm != null
                        ? "Roll"
                        : "—"}
                  </span>
                  <span className="qb-calc-label">Sheets required</span>
                  <span className="qb-calc-value">
                    {calcResult.part.production?.quantities?.sheets_required ??
                      calcResult.part.selected_sheet?.sheets_required ??
                      "—"}
                  </span>
                  <span className="qb-calc-label">Per sheet</span>
                  <span className="qb-calc-value">
                    {calcResult.part.selected_sheet?.per_sheet ?? "—"}
                  </span>
                  <span className="qb-calc-label">Waste %</span>
                  <span className="qb-calc-value">
                    {calcResult.part.selected_sheet != null
                      ? ((calcResult.part.selected_sheet.waste_pct ?? 0) * 100).toFixed(1) + "%"
                      : "—"}
                  </span>
                  {(() => {
                    const time = calcResult.part.production?.time;
                    if (!time) return null;
                    const speedWarning = calcResult.part.production?.warnings?.find((w: string) =>
                      w.includes("speed_sqm_per_hour")
                    );
                    return (
                      <>
                        <span className="qb-calc-label">Setup</span>
                        <span className="qb-calc-value">{time.setup_min != null ? `${time.setup_min} min` : "—"}</span>
                        <span className="qb-calc-label">Print</span>
                        <span className="qb-calc-value">
                          {time.print_min != null ? (
                            `${time.print_min} min`
                          ) : speedWarning ? (
                            <Tooltip content={speedWarning}>
                              <span>—</span>
                            </Tooltip>
                          ) : (
                            "—"
                          )}
                        </span>
                        <span className="qb-calc-label">Total time</span>
                        <span className="qb-calc-value">{time.total_min != null ? `${time.total_min} min` : "—"}</span>
                      </>
                    );
                  })()}
                  {(() => {
                    const ink = calcResult.part.production?.ink;
                    if (!ink) return null;
                    const inkWarning = calcResult.part.production?.warnings?.find((w: string) =>
                      w.includes("ink") || w.includes("machine.meta")
                    );
                    if (inkWarning && (ink.ink_cost_gbp == null || ink.ink_cost_gbp === 0)) {
                      return (
                        <>
                          <span className="qb-calc-label">Ink</span>
                          <span className="qb-calc-value qb-calc-warning-text" title={inkWarning}>
                            {inkWarning}
                          </span>
                        </>
                      );
                    }
                    return (
                      <>
                        <span className="qb-calc-label">Ink</span>
                        <span className="qb-calc-value qb-calc-money">
                          £{ink.ink_cost_gbp?.toFixed(2) ?? "0.00"}
                          {ink.ink_ml != null && ink.coverage_pct != null
                            ? ` (${ink.ink_ml} ml @ ${ink.coverage_pct}%)`
                            : ""}
                        </span>
                      </>
                    );
                  })()}
                </div>
              </div>

              {/* Section 2: Cost Summary */}
              <div className="qb-calc-section">
                <div className="qb-calc-section-title">Cost summary</div>
                <div className="qb-calc-grid">
                  <span className="qb-calc-label">Material cost</span>
                  <span className="qb-calc-value qb-calc-money">
                    £{calcResult.part.material_cost?.toFixed(2) ?? "—"}
                  </span>
                  {(() => {
                    const rates = calcResult.part.production?.rates_applied ?? [];
                    const printCost = rates
                      .filter((r: any) => r.operation_key === "print_sqm")
                      .reduce((s: number, r: any) => s + (r.cost_gbp ?? 0), 0);
                    const laminateCost = rates
                      .filter((r: any) => r.operation_key === "laminate_sqm")
                      .reduce((s: number, r: any) => s + (r.cost_gbp ?? 0), 0);
                    const inkCost = rates
                      .filter((r: any) => r.operation_key === "white_ink_sqm")
                      .reduce((s: number, r: any) => s + (r.cost_gbp ?? 0), 0);
                    const prodInk = calcResult.part.production?.ink;
                    const prodInkCost = prodInk?.ink_cost_gbp ?? 0;
                    return (
                      <>
                        {printCost > 0 && (
                          <>
                            <span className="qb-calc-label">Print cost</span>
                            <span className="qb-calc-value qb-calc-money">£{printCost.toFixed(2)}</span>
                          </>
                        )}
                        {laminateCost > 0 && (
                          <>
                            <span className="qb-calc-label">Laminate cost</span>
                            <span className="qb-calc-value qb-calc-money">£{laminateCost.toFixed(2)}</span>
                          </>
                        )}
                        {inkCost > 0 && (
                          <>
                            <span className="qb-calc-label">White ink cost</span>
                            <span className="qb-calc-value qb-calc-money">£{inkCost.toFixed(2)}</span>
                          </>
                        )}
                        {prodInk != null && (
                          <>
                            <span className="qb-calc-label">Ink</span>
                            <span className="qb-calc-value qb-calc-money">£{prodInkCost.toFixed(2)}</span>
                          </>
                        )}
                      </>
                    );
                  })()}
                  <span className="qb-calc-label">Total cost</span>
                  <span className="qb-calc-value qb-calc-money qb-calc-emphasis">
                    £{calcResult.part.total_cost?.toFixed(2) ?? "—"}
                  </span>
                  <span className="qb-calc-label">Sell</span>
                  <span className="qb-calc-value qb-calc-money qb-calc-emphasis">
                    £{calcResult.part.sell_price?.toFixed(2) ?? "—"}
                  </span>
                </div>
              </div>

              <div className="qb-calc-tabs">
                {[
                  ["alternatives", "Alternatives"],
                  ...(calcResult?.part?.production ? [["production", "Production"]] : []),
                  ["warnings", "Warnings"],
                ].map(([k, l]) => (
                  <button
                    key={k}
                    type="button"
                    className={`qb-calc-tab ${calcTab === k ? "qb-calc-tab-active" : ""}`}
                    onClick={() => setCalcTab(k)}
                  >
                    {l}
                  </button>
                ))}
              </div>

              {calcTab === "alternatives" && (
                <div>
                  {calcResult.part.alternatives?.length > 0 ? (
                    <table className="qb-calc-rates-table">
                      <thead>
                        <tr>
                          <th>Sheet size</th>
                          <th className="num">Per sheet</th>
                          <th className="num">Sheets</th>
                          <th className="num">Waste %</th>
                          <th className="num">Mat. cost</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {calcResult.part.alternatives.map((alt: any) => (
                          <tr key={alt.sheet_size_id ?? `${alt.width_mm}x${alt.height_mm}`}>
                            <td>{alt.width_mm}×{alt.height_mm} mm</td>
                            <td className="num">{alt.per_sheet}</td>
                            <td className="num">{alt.sheets_required}</td>
                            <td className="num">{((alt.waste_pct ?? 0) * 100).toFixed(1)}%</td>
                            <td className="num">£{alt.material_cost?.toFixed(2) ?? "—"}</td>
                            <td>
                              {alt.sheet_size_id && (
                                <button
                                  type="button"
                                  className="primary"
                                  style={{ padding: "4px 10px", fontSize: 12 }}
                                  onClick={() => useSheetSize(alt.sheet_size_id)}
                                >
                                  Use
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="subtle" style={{ padding: "16px 0" }}>No alternatives.</div>
                  )}
                </div>
              )}

              {calcTab === "production" && (
                <div>
                  {calcResult.part?.production?.warnings?.length > 0 && (
                    <div className="qb-calc-warning" style={{ marginBottom: 16 }}>
                      <strong>Config warnings:</strong>
                      <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
                        {calcResult.part.production.warnings.map((w: string, i: number) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {(() => {
                    const time = calcResult.part.production?.time;
                    const ink = calcResult.part.production?.ink;
                    const speedWarning = calcResult.part.production?.warnings?.find((w: string) =>
                      w.includes("speed_sqm_per_hour")
                    );
                    const inkWarning = calcResult.part.production?.warnings?.find((w: string) =>
                      w.includes("ink") || w.includes("machine.meta")
                    );
                    return (time || ink) ? (
                      <div className="qb-calc-section" style={{ marginBottom: 16 }}>
                        <div className="qb-calc-section-title">Machine time & ink</div>
                        <div className="qb-calc-grid">
                          {time && (
                            <>
                              <span className="qb-calc-label">Setup</span>
                              <span className="qb-calc-value">{time.setup_min != null ? `${time.setup_min} min` : "—"}</span>
                              <span className="qb-calc-label">Print</span>
                              <span className="qb-calc-value">
                                {time.print_min != null ? (
                                  `${time.print_min} min`
                                ) : speedWarning ? (
                                  <Tooltip content={speedWarning}>
                                    <span>—</span>
                                  </Tooltip>
                                ) : (
                                  "—"
                                )}
                              </span>
                              <span className="qb-calc-label">Total</span>
                              <span className="qb-calc-value">{time.total_min != null ? `${time.total_min} min` : "—"}</span>
                            </>
                          )}
                          {ink && (
                            <>
                              <span className="qb-calc-label">Ink</span>
                              <span className="qb-calc-value">
                                {inkWarning && (ink.ink_cost_gbp == null || ink.ink_cost_gbp === 0) ? (
                                  <span className="qb-calc-warning-text" title={inkWarning}>{inkWarning}</span>
                                ) : (
                                  <>£{ink.ink_cost_gbp?.toFixed(2) ?? "0.00"} ({ink.ink_ml ?? 0} ml @ {ink.coverage_pct ?? 15}%)</>
                                )}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    ) : null;
                  })()}
                  {calcResult.part.production?.rates_applied?.length ? (
                    <table className="qb-calc-rates-table">
                      <thead>
                        <tr>
                          <th>Operation</th>
                          <th className="num">Qty</th>
                          <th>Unit</th>
                          <th className="num">Unit cost</th>
                          <th className="num">Setup min</th>
                          <th className="num">Min charge</th>
                          <th className="num">Cost</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calcResult.part.production.rates_applied.map((r: any, i: number) => (
                          <tr key={i}>
                            <td>{r.operation_key ?? "—"}</td>
                            <td className="num">{r.qty ?? "—"}</td>
                            <td>{r.unit ?? "—"}</td>
                            <td className="num">£{(r.unit_cost_gbp ?? 0).toFixed(2)}</td>
                            <td className="num">{r.setup_minutes ?? "—"}</td>
                            <td className="num">£{(r.min_charge_gbp ?? 0).toFixed(2)}</td>
                            <td className="num">£{(r.cost_gbp ?? 0).toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="subtle" style={{ padding: "16px 0" }}>No rates applied.</div>
                  )}
                </div>
              )}

              {calcTab === "warnings" && (
                <div>
                  {calcResult.warnings?.length > 0 ? (
                    <div className="qb-calc-warnings-list">
                      {calcResult.warnings.map((w: string, i: number) => (
                        <div key={i} className="qb-calc-warning">
                          ⚠ {w}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="subtle" style={{ padding: "16px 0" }}>No warnings.</div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="subtle">No calculation result.</div>
          )}
        </Drawer>

        {/* Command palette */}
        <CommandPalette
          open={cmdPaletteOpen}
          onClose={() => setCmdPaletteOpen(false)}
          items={cmdItems}
          placeholder="Search commands… (⌘K)"
        />
      </div>
    </div>
  );
}

export default function QuoteBuilder({
  params,
}: {
  params: { id: string };
}) {
  const id = params.id as string;
  return (
    <ToastProvider>
      <QuoteBuilderInner id={id} params={params} />
    </ToastProvider>
  );
}
