import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl } from "@/lib/backendProxy";

/**
 * Server-side proxy to FastAPI. Replaces `next.config` rewrites so
 * `Set-Cookie` from `POST /api/auth/login` reaches the browser reliably.
 */
export const runtime = "nodejs";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
]);

/** Headers that confuse clients if copied after Node fetch may have decoded the body. */
const STRIP_FROM_UPSTREAM = new Set([
  ...HOP_BY_HOP,
  "content-encoding",
  "content-length",
]);

function copyUpstreamHeaders(from: Headers, to: NextResponse) {
  from.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "set-cookie") return;
    if (STRIP_FROM_UPSTREAM.has(lower)) return;
    to.headers.set(key, value);
  });

  const multi = typeof from.getSetCookie === "function" ? from.getSetCookie() : null;
  if (multi && multi.length) {
    for (const c of multi) {
      to.headers.append("Set-Cookie", c);
    }
    return;
  }
  const single = from.get("set-cookie");
  if (single) {
    to.headers.append("Set-Cookie", single);
  }
}

async function proxy(req: NextRequest, segments: string[]) {
  const target = backendApiUrl(segments, req.nextUrl.search);

  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("content-length");

  const hasBody = !["GET", "HEAD"].includes(req.method);
  const init: RequestInit & { duplex?: string } = {
    method: req.method,
    headers,
    redirect: "manual",
  };
  if (hasBody) {
    init.body = req.body;
    init.duplex = "half";
  }

  const upstream = await fetch(target, init);

  const res = new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
  });

  copyUpstreamHeaders(upstream.headers, res);
  return res;
}

type RouteCtx = { params: Promise<{ path?: string[] }> };

async function handle(req: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
export const HEAD = handle;
