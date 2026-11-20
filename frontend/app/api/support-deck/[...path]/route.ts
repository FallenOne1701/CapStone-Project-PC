import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

function supportDeckBase(): string {
  const raw =
    process.env.SUPPORT_DECK_URL?.trim() ||
    process.env.NEXT_PUBLIC_SUPPORT_DECK_URL?.trim() ||
    "http://127.0.0.1:8001";
  return raw.replace(/\/+$/, "");
}

type RouteCtx = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, pathSegments: string[]) {
  const base = supportDeckBase();
  const suffix = pathSegments.map(encodeURIComponent).join("/");
  const target = `${base}/api/support-deck/${suffix}${request.nextUrl.search}`;

  const headers: Record<string, string> = { Accept: "application/json" };
  const method = request.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";
  const body = hasBody ? await request.text() : undefined;
  if (hasBody) {
    headers["Content-Type"] =
      request.headers.get("Content-Type") || "application/json";
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
    });
  } catch (err) {
    const why = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        detail: `Could not reach Support Deck API at ${base} (${why}). Is it running on port 8001? Set SUPPORT_DECK_URL for the Next.js server.`,
      },
      { status: 502 },
    );
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") || "application/json",
    },
  });
}

export async function GET(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}
