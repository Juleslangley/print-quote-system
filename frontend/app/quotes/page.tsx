"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
// Using Modal from app/_components/Modal
import Modal from "@/app/_components/Modal";

const JOB_TYPE_OPTIONS = [
  { value: "LARGE_FORMAT_SHEET", label: "Large Format sheet" },
  { value: "LARGE_FORMAT_ROLL", label: "Large Format Roll" },
  { value: "LITHO_SHEET", label: "Litho sheet" },
  { value: "DIGITAL_SHEET", label: "Digital sheet" },
] as const;

export default function Quotes() {
  const router = useRouter();
  const [customers, setCustomers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [error, setError] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [customerId, setCustomerId] = useState("");
  const [quoteName, setQuoteName] = useState("");
  const [defaultJobType, setDefaultJobType] = useState("LARGE_FORMAT_SHEET");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setNeedsLogin(false);
      try {
        const c = await api<any[]>("/api/customers");
        setCustomers(c ?? []);
      } catch {
        setNeedsLogin(true);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function createQuote() {
    setError("");
    if (!customerId) {
      setError("Select a customer");
      return;
    }
    setSubmitting(true);
    try {
      const q = await api<{ id: string }>("/api/quotes", {
        method: "POST",
        body: JSON.stringify({
          customer_id: customerId,
          name: quoteName.trim() || undefined,
          default_job_type: defaultJobType,
        }),
      });
      setCreateModalOpen(false);
      setCustomerId("");
      setQuoteName("");
      setDefaultJobType("LARGE_FORMAT_SHEET");
      router.push(`/quotes/${q.id}`);
    } catch (e: any) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div><h1>Quotes</h1><p>Loading…</p></div>;

  if (needsLogin) {
    return (
      <div>
        <h1>Quotes</h1>
        <p>Please log in to see customers and create quotes.</p>
        <p><Link href="/">Go to login</Link></p>
      </div>
    );
  }

  return (
    <div>
      <h1>Quotes</h1>
      <p>
        <button onClick={() => setCreateModalOpen(true)}>Create Quote</button>
      </p>

      <Modal
        open={createModalOpen}
        title="Create Quote"
        onClose={() => setCreateModalOpen(false)}
        confirmOnClose={false}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <label>
            Customer
            <select
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              style={{ display: "block", width: "100%", padding: 8, marginTop: 4 }}
            >
              <option value="">— Select —</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>
          <label>
            Quote name
            <input
              type="text"
              value={quoteName}
              onChange={(e) => setQuoteName(e.target.value)}
              placeholder="e.g. Brochure print Jan 2025"
              style={{ display: "block", width: "100%", padding: 8, marginTop: 4 }}
            />
          </label>
          <label>
            Default job type (optional, for new parts)
            <select
              value={defaultJobType}
              onChange={(e) => setDefaultJobType(e.target.value)}
              style={{ display: "block", width: "100%", padding: 8, marginTop: 4 }}
            >
              {JOB_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          {error && <p style={{ color: "#c00", margin: 0 }}>{error}</p>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
            <button type="button" onClick={() => setCreateModalOpen(false)}>Cancel</button>
            <button type="button" onClick={createQuote} disabled={submitting}>
              {submitting ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
