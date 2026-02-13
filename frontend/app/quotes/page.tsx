"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function Quotes() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [quoteId, setQuoteId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [error, setError] = useState("");

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

  async function createQuote(customer_id: string) {
    setError("");
    try {
      const q = await api<{ id: string }>("/api/quotes", { method: "POST", body: JSON.stringify({ customer_id }) });
      setQuoteId(q.id);
    } catch (e: any) {
      setError(e?.message || "Failed to create quote");
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
      <p>Select a customer to create a quote.</p>

      {customers.length === 0 ? (
        <p>No customers yet. Add one via the API or seed again.</p>
      ) : (
        <ul>
          {customers.map((c) => (
            <li key={c.id}>
              {c.name} <button onClick={() => createQuote(c.id)}>Create Quote</button>
            </li>
          ))}
        </ul>
      )}

      {error && <p style={{ color: "red" }}>{error}</p>}

      {quoteId && (
        <p>
          Created quote: <a href={`/quotes/${quoteId}`}>Open quote</a>
        </p>
      )}
    </div>
  );
}
