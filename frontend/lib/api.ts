export class ApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string) {
    super(`API ${status}: ${body}`);
    this.status = status;
    this.body = body;
  }
}

export async function api(path: string, opts: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const headers: Record<string, string> = { ...(opts.headers as Record<string, string>) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  // Do not set Content-Type for FormData; browser sets multipart/form-data with boundary
  if (!(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  // IMPORTANT: same-origin call. Next.js will rewrite /api/* to backend.
  const res = await fetch(path.startsWith("/api") ? path : `/api${path}`, {
    ...opts,
    headers,
  });

  const text = await res.text();
  if (!res.ok) throw new ApiError(res.status, text || res.statusText);

  if (!text.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
