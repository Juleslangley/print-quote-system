"use client";

import { useState } from "react";
import { api } from "../lib/api";

export default function Home() {
  const [email, setEmail] = useState("admin@local");
  const [password, setPassword] = useState("admin123");
  const [msg, setMsg] = useState("");

  async function seed() {
    try {
      const res = await fetch("/api/seed/dev", { method: "POST" });
      setMsg("Seed: " + (await res.text()));
    } catch (e: any) {
      setMsg("Seed error: " + (e?.message || String(e)));
    }
  }

  async function login() {
    const out = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }) as { access_token?: string };
    const token = out?.access_token;
    if (token) localStorage.setItem("token", token);
    setMsg(token ? "Logged in." : "Login failed (no token).");
  }

  return (
    <div>
      <h1>Print Quote System</h1>

      <button onClick={seed}>Seed Dev Data</button>
      <p style={{ fontSize: 14, color: "#555" }}>Run this first if the database is empty (creates admin, sales, production users).</p>

      <h2>Login</h2>
      <p style={{ fontSize: 14, marginBottom: 8 }}>
        <strong>Admin:</strong> admin@local / admin123 &nbsp;|&nbsp; <strong>Sales:</strong> sales@local / sales123 &nbsp;|&nbsp; <strong>Production:</strong> production@local / prod123
      </p>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" style={{ minWidth: 160 }} />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" style={{ minWidth: 120 }} />
        <button onClick={login}>Login</button>
      </div>

      <p style={{ whiteSpace: "pre-wrap" }}>{msg}</p>

      <p>
        Go to <a href="/quotes">Quotes</a>
      </p>
    </div>
  );
}
