"use client";

import { useEffect, useState } from "react";
import { getApiLog, getLastApiError } from "@/lib/api";

const MAX_DISPLAY = 10;

export default function DevDebugPanel() {
  const [entries, setEntries] = useState<ReturnType<typeof getApiLog>>([]);
  const [lastErr, setLastErr] = useState<ReturnType<typeof getLastApiError>>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    const tick = () => {
      setEntries(getApiLog().slice(-MAX_DISPLAY));
      setLastErr(getLastApiError());
    };
    tick();
    const id = setInterval(tick, 500);
    return () => clearInterval(id);
  }, []);

  if (process.env.NODE_ENV !== "development") return null;

  return (
    <div style={{ position: "fixed", top: 8, right: 8, zIndex: 99999 }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          padding: "4px 8px",
          fontSize: 11,
          background: "#333",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: "pointer",
        }}
      >
        Dev
      </button>
      {open && (
        <div
          style={{
            marginTop: 4,
            padding: 8,
            background: "#1e1e1e",
            color: "#d4d4d4",
            fontSize: 11,
            maxWidth: 320,
            maxHeight: 280,
            overflow: "auto",
            borderRadius: 6,
            border: "1px solid #444",
          }}
        >
          <div style={{ marginBottom: 6, fontWeight: 600 }}>Last {MAX_DISPLAY} API</div>
          {entries.length === 0 && <div style={{ color: "#858585" }}>No requests yet</div>}
          {entries.map((e, i) => (
            <div key={i} style={{ marginBottom: 2 }}>
              <span style={{ color: e.status >= 400 ? "#f48771" : "#4ec9b0" }}>{e.status}</span> {e.method} {e.url}
            </div>
          ))}
          {lastErr && (
            <>
              <div style={{ marginTop: 8, marginBottom: 4, fontWeight: 600, color: "#f48771" }}>Last error</div>
              <div style={{ marginBottom: 2 }}>{lastErr.message}</div>
              <div style={{ fontSize: 10, color: "#858585" }}>status={lastErr.status} body={lastErr.body.slice(0, 80)}{lastErr.body.length > 80 ? "…" : ""}</div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
