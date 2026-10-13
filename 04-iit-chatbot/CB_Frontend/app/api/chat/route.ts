import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL, backendHeaders } from "../../lib/backend";

// Render free instances can take ~1 min to wake; don't let the function give up first.
export const maxDuration = 60;

export async function POST(req: NextRequest) {
  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
    const res = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: backendHeaders(req),
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      // Turn backend errors (429 rate limit, 500, …) into a normal chat bubble and keep the
      // user's session memory instead of wiping it.
      let detail = "The assistant is unavailable right now. Please try again shortly.";
      try {
        const err = await res.json();
        if (typeof err?.detail === "string") detail = err.detail;
      } catch {}
      return NextResponse.json({
        answer_markdown: `⚠️ ${detail}`,
        mode: "error",
        topic: null,
        memory: body.memory ?? {},
      });
    }

    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({
      answer_markdown:
        "⚠️ Could not reach the assistant. If it has been idle it may be waking up — please try again in a minute.",
      mode: "error",
      topic: null,
      memory: body.memory ?? {},
    });
  }
}
