import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const DEFAULT_BACKEND_TIMEOUT_MS = 55_000;

function getBackendTimeoutMs(): number {
  const rawValue = process.env.BACKEND_CRON_TIMEOUT_MS;
  if (!rawValue) {
    return DEFAULT_BACKEND_TIMEOUT_MS;
  }

  const parsedValue = Number(rawValue);
  if (!Number.isFinite(parsedValue) || parsedValue <= 0) {
    return DEFAULT_BACKEND_TIMEOUT_MS;
  }

  return parsedValue;
}

async function parseBackendBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function GET(request: NextRequest) {
  const cronSecret = process.env.CRON_SECRET;
  const authHeader = request.headers.get("authorization");

  if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
    return Response.json({ ok: false, error: "Unauthorized" }, { status: 401 });
  }

  const backendCronUrl = process.env.BACKEND_CRON_URL;
  if (!backendCronUrl) {
    return Response.json(
      { ok: false, error: "BACKEND_CRON_URL is not configured" },
      { status: 500 },
    );
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), getBackendTimeoutMs());

  try {
    const response = await fetch(backendCronUrl, {
      method: "GET",
      headers: {
        authorization: `Bearer ${cronSecret}`,
      },
      cache: "no-store",
      signal: controller.signal,
    });
    const backendBody = await parseBackendBody(response);

    return Response.json(
      {
        ok: response.ok,
        backendStatus: response.status,
        backend: backendBody,
      },
      { status: response.ok ? 200 : 502 },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown cron error";
    return Response.json({ ok: false, error: message }, { status: 504 });
  } finally {
    clearTimeout(timeout);
  }
}
