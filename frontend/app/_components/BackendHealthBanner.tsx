"use client";

import { useEffect, useState } from "react";

export default function BackendHealthBanner() {
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health", { credentials: "same-origin" })
      .then((res) => {
        if (!cancelled && !res.ok) setBackendDown(true);
      })
      .catch(() => {
        if (!cancelled) setBackendDown(true);
      });
    return () => {
      cancelled = true;
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
      Backend container not healthy
    </div>
  );
}
