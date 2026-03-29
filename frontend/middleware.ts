import { NextRequest, NextResponse } from "next/server";
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

const BLOCKED_IPS = new Set([
  "88.216.210.27", // Chrome/91 scraper bot
]);

const intlMiddleware = createMiddleware(routing);

export default function middleware(request: NextRequest) {
  // Block known scraper IPs
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    request.ip ||
    "";
  if (BLOCKED_IPS.has(ip)) {
    return new NextResponse("Forbidden", { status: 403 });
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: "/((?!api|trpc|_next|_vercel|.*\\..*).*)",
};
