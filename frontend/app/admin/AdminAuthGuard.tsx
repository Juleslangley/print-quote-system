"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function AdminAuthGuard({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api
      .get("/api/me")
      .then(() => setReady(true))
      .catch(() => {
        // 401: api.ts clears token and redirects to /
        // Other errors: still show children so the page can display error
        setReady(true);
      });
  }, []);

  if (!ready) {
    return (
      <div style={{ padding: 24, color: "#666" }}>
        Checking auth…
      </div>
    );
  }
  return <>{children}</>;
}
