// middleware.ts — route protection
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED = ["/history"];
const AUTH_ONLY = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get("aqi_token")?.value;
  const { pathname } = request.nextUrl;

  if (PROTECTED.some((p) => pathname.startsWith(p)) && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (AUTH_ONLY.some((p) => pathname.startsWith(p)) && token) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/history/:path*", "/login", "/register"],
};
