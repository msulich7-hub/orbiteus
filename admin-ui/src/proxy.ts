/**
 * Edge proxy (Next 16 successor to `middleware.ts`): server-side auth gate.
 *
 * Eliminates the Flash Of Authenticated Content by redirecting unauthenticated
 * users to /login *before* any RSC/HTML is generated. Walks the same cookie
 * the backend sets on /api/auth/login (`orbiteus_token`).
 *
 * Public surface: /welcome, /login, /api proxy, _next assets, branding/static.
 *
 * See docs/adr/0017-httponly-cookie-session.md.
 */
import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = new Set<string>(["/login", "/welcome"]);

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (PUBLIC_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  const token = req.cookies.get("orbiteus_token")?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // Run on every page route. Skip Next assets, /api proxy (handled by backend),
  // favicon and static branding.
  matcher: ["/((?!_next|api|favicon|branding|robots\\.txt).*)"],
};
