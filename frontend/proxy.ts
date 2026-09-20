import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const token = request.cookies.get("token")?.value;
  const { pathname } = request.nextUrl;
  const publicRoute = pathname === "/login" || pathname.startsWith("/_next") || pathname.includes("favicon.ico");
  if (!token && !publicRoute) return NextResponse.redirect(new URL("/login", request.url));
  if (token && pathname === "/login") return NextResponse.redirect(new URL("/", request.url));
  return NextResponse.next();
}

export const config = { matcher: ["/((?!api|_next/static|_next/image|favicon.ico|assets|uploads).*)"] };
