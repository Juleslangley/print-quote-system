/**
 * API helper: same-origin requests to backend (Next.js rewrites /api/*).
 * - Sends Authorization: Bearer <token> for all methods when token exists (localStorage, same key as login).
 * - Always sends Accept: application/json.
 * - JSON body: Content-Type: application/json.
 * - Errors throw ApiError with status, message, and optional details; UI can show error.message and error.details.
 */

const TOKEN_KEY = "token";

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

function errorMessageFromDetails(body: string, status: number, details: unknown): string {
  let msg: string;
  if (details === null || details === undefined) {
    msg = body || `Request failed with status ${status}`;
  } else if (typeof details !== "object" || !("detail" in details)) {
    msg = body || `Request failed with status ${status}`;
  } else {
    const d = (details as { detail?: unknown }).detail;
    if (typeof d === "string") msg = d;
    else if (Array.isArray(d)) {
      msg = d.map((e: { msg?: string; loc?: unknown }) => e?.msg || JSON.stringify(e)).join("; ") || body || `Request failed with status ${status}`;
    } else {
      msg = typeof d === "object" ? JSON.stringify(d) : String(d ?? body ?? `Request failed with status ${status}`);
    }
  }
  return `${status}: ${msg}`;
}

export class ApiError extends Error {
  status: number;
  body: string;
  /** Parsed JSON when response was JSON (e.g. { detail: "..." }). */
  details?: unknown;

  constructor(status: number, body: string, details?: unknown) {
    let msg = errorMessageFromDetails(body, status, details);
    if (status === 500 && body) {
      msg += ` — Response: ${body.slice(0, 300)}${body.length > 300 ? "…" : ""}`;
    }
    super(msg);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.details = details;
  }
}

export async function api(path: string, opts: RequestInit = {}): Promise<unknown> {
  const token = getToken();
  const url = path.startsWith("/api") ? path : `/api${path}`;

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (opts.body !== undefined && opts.body !== null) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method: opts.method,
      credentials: opts.credentials ?? "same-origin",
      mode: opts.mode,
      cache: opts.cache,
      redirect: opts.redirect,
      referrer: opts.referrer,
      integrity: opts.integrity,
      keepalive: opts.keepalive,
      signal: opts.signal,
      body: opts.body,
      headers,
    });
  } catch (err) {
    const method = (opts.method || "GET").toUpperCase();
    if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
      console.log("[api]", method, url, "network error");
    }
    pushApiError({ message: "Backend offline", status: 0, body: "", ts: Date.now() });
    throw new ApiError(0, "Backend offline");
  }

  const text = await res.text();
  const method = (opts.method || "GET").toUpperCase();
  if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
    console.log("[api]", method, url, res.status);
  }
  pushApiLog({ method, url, status: res.status, ts: Date.now() });

  if (!res.ok) {
    let details: unknown;
    try {
      details = text ? JSON.parse(text) : undefined;
    } catch {
      details = undefined;
    }
    pushApiError({
      message: errorMessageFromDetails(text || res.statusText, res.status, details),
      status: res.status,
      body: text || "",
      ts: Date.now(),
    });
    if (typeof window !== "undefined") {
      console.error("[api] Request failed:", { url, method, status: res.status, responseBody: text || "(empty)" });
    }
    throw new ApiError(res.status, text || res.statusText, details);
  }

  if (!text.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
