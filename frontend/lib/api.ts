/**
 * Shared API helper for the frontend.
 * - Base URL: process.env.NEXT_PUBLIC_BACKEND_URL or fallback "http://localhost:8000".
 * - Sends Authorization: Bearer <token> when token exists (localStorage).
 * - Safe JSON parsing; throws ApiError on non-2xx responses.
 * - api.get<T>(), api.post<T>(), api.patch<T>(); also api(path, opts) for custom requests.
 */

const TOKEN_KEY = "token";

const DEFAULT_BACKEND_URL = "http://localhost:8000";

function getBaseUrl(): string {
  // In the browser, use same-origin so /api/* goes through Next.js rewrites to the backend (avoids CORS and "Backend offline" when backend is only reachable via the dev server).
  if (typeof window !== "undefined") return "";
  if (typeof process === "undefined" || !process.env) return DEFAULT_BACKEND_URL;
  const url = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (url && typeof url === "string") return url.replace(/\/$/, "");
  return DEFAULT_BACKEND_URL;
}

const MAX_LOG = 20;
export type ApiLogEntry = { method: string; url: string; status: number; ts: number };
export type ApiErrorEntry = { message: string; status: number; body: string; ts: number };

const apiLog: ApiLogEntry[] = [];
let lastError: ApiErrorEntry | null = null;

export function pushApiLog(entry: ApiLogEntry): void {
  apiLog.push(entry);
  if (apiLog.length > MAX_LOG) apiLog.shift();
}

export function pushApiError(entry: ApiErrorEntry): void {
  lastError = entry;
}

export function getApiLog(): ApiLogEntry[] {
  return [...apiLog];
}

export function getLastApiError(): ApiErrorEntry | null {
  return lastError;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

/** Store token after login. Use this so the key is consistent. */
export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
    window.dispatchEvent(new Event("auth-change"));
  }
}

/** Clear token (logout or after 401). */
export function clearToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event("auth-change"));
  }
}

function errorMessageFromDetails(body: string, status: number, details: unknown): string {
  if (details === null || details === undefined) return body || `Request failed with status ${status}`;
  if (typeof details !== "object" || !("detail" in details)) return body || `Request failed with status ${status}`;
  const d = (details as { detail?: unknown }).detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e: { msg?: string }) => e?.msg || JSON.stringify(e)).join("; ") || body || `Request failed with status ${status}`;
  return typeof d === "object" ? JSON.stringify(d) : String(d ?? body ?? `Request failed with status ${status}`);
}

export class ApiError extends Error {
  status: number;
  body: string;
  details?: unknown;

  constructor(status: number, body: string, details?: unknown) {
    let msg = errorMessageFromDetails(body, status, details);
    if (status === 500 && body) msg += ` — Response: ${body.slice(0, 300)}${body.length > 300 ? "…" : ""}`;
    super(msg);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.details = details;
  }
}

function resolveUrl(path: string): string {
  const p = path.startsWith("/api") ? path : `/api${path}`;
  const base = getBaseUrl();
  return base ? `${base}${p}` : p;
}

async function request<T = unknown>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const url = resolveUrl(path);
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (opts.body !== undefined && opts.body !== null && !(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(url, { ...opts, credentials: opts.credentials ?? "same-origin", headers });
  } catch {
    pushApiError({ message: "Backend offline", status: 0, body: "", ts: Date.now() });
    throw new ApiError(0, "Backend offline");
  }

  const text = await res.text();
  const method = (opts.method || "GET").toUpperCase();
  pushApiLog({ method, url, status: res.status, ts: Date.now() });
  if (res.status === 405) {
    console.warn("[API 405] Method Not Allowed:", method, url);
  }

  if (!res.ok) {
    let details: unknown;
    try {
      details = text ? JSON.parse(text) : undefined;
    } catch {
      details = undefined;
    }
    pushApiError({ message: errorMessageFromDetails(text || res.statusText, res.status, details), status: res.status, body: text || "", ts: Date.now() });
    if (res.status === 401) {
      clearToken();
      const isAuthCheck = path === "/api/auth/me" || path === "/api/me";
      if (!isAuthCheck && typeof window !== "undefined") window.location.href = "/";
    }
    throw new ApiError(res.status, text || res.statusText, details);
  }

  if (!text.trim()) return null as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as T;
  }
}

/**
 * Fetch with auth (same as api). Use for blob/binary responses (e.g. PDF download).
 * Returns raw Response; caller must check res.ok and handle 401.
 */
export async function apiFetch(path: string, opts: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const url = resolveUrl(path);
  const headers: Record<string, string> = {
    ...((opts.headers as Record<string, string>) ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(url, {
    ...opts,
    credentials: opts.credentials ?? "include",
    headers: { ...opts.headers, ...headers },
  });
}

export const api = Object.assign(
  <T = unknown>(path: string, init?: RequestInit): Promise<T> => request<T>(path, init),
  {
    get: <T = unknown>(path: string, opts?: RequestInit) => request<T>(path, { ...opts, method: "GET" }),
    post: <T = unknown>(path: string, body?: unknown, opts?: RequestInit) =>
      request<T>(path, { ...opts, method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
    patch: <T = unknown>(path: string, body?: unknown, opts?: RequestInit) =>
      request<T>(path, { ...opts, method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  }
);
