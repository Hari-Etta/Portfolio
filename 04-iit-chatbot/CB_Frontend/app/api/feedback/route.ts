import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL, backendHeaders } from "../../lib/backend";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${BACKEND_URL}/api/feedback`, {
      method: "POST",
      headers: backendHeaders(req),
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Feedback failed" }, { status: 500 });
  }
}
