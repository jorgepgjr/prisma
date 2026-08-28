import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("token")?.value;
  const { pathname } = request.nextUrl;

  // Rotas públicas (tela de login, assets estáticos, etc)
  const isPublicRoute = 
    pathname === "/login" || 
    pathname.startsWith("/_next") || 
    pathname.includes("/favicon.ico");

  if (!token && !isPublicRoute) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  if (token && pathname === "/login") {
    const dashboardUrl = new URL("/", request.url);
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Executa o middleware em todas as rotas exceto assets e arquivos de api
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|assets|uploads).*)"],
};
