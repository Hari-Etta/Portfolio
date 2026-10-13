import { NextRequest } from "next/server";

export const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

/**
 * Headers for server-to-server calls to the FastAPI backend.
 * PROXY_SECRET (server-only env var, never exposed to the browser) proves the call came
 * through this proxy; X-Client-IP lets the backend rate-limit per visitor instead of
 * treating every user as Netlify's single IP.
 */
export function backendHeaders(req: NextRequest): Record<string, string> {
  const clientIp =
    req.headers.get("x-nf-client-connection-ip") ||
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    "unknown";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Client-IP": clientIp,
  };
  if (process.env.PROXY_SECRET) headers["X-Proxy-Secret"] = process.env.PROXY_SECRET;
  return headers;
}
