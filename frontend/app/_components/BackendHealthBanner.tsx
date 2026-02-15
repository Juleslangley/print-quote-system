"use client";

import { useEffect, useState } from "react";

export default function BackendHealthBanner() {
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      fetch("/api/health", { credentials: "same-origin" })
        .then((res) => {
          if (!cancelled && res.ok) setBackendDown(false);
          else if (!cancelled) setBackendDown(true);
        })
        .catch(() => {
          if (!cancelled) setBackendDown(true);
        });
    };
    check();
    const interval = setInterval(check, 8000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (!backendDown) return null;

  return (
    <div
      style={{
        background: "#c00",
        color: "#fff",
        padding: "10px 16px",
        textAlign: "center",
        fontSize: 14,
      }}
    >
      Backend offline. Start the backend (e.g. <code style={{ background: "rgba(0,0,0,0.2)", padding: "2px 6px", borderRadius: 4 }}>npm run dev:backend</code> from the frontend directory) and ensure it runs on port 8000.
    </div>
  );
}
