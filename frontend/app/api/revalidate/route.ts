/**
 * Sprint 27 — explicit ISR cache invalidation after admin edits.
 * Sprint 28 update — also invalidate the dynamic-route segment so the
 * slug URL the user lands on AFTER the redirect is busted, not just
 * the bare-code URL.
 *
 * Problem: school detail pages have `revalidate=86400`. Without
 * explicit invalidation, edits don't appear for up to 24h. Sprint 28
 * additionally introduced slug URLs (`/school/<name>-<city>-<moe>`);
 * the bare-code URL 301s to the slug, but the SLUG page itself is
 * ISR-cached. Without busting the slug, the user lands on a stale
 * page even after the bare-code revalidation fires.
 *
 * Fix: revalidate the entire `/[locale]/school/[moe_code]` dynamic
 * segment with type `page` — Next invalidates every cached instance
 * of that route, regardless of slug shape. This covers the bare-code
 * URL, the new canonical slug URL, AND any stale slug from a previous
 * name/city. Heavier than per-URL revalidation but correct, and the
 * extra cost is negligible (each cached school page just regenerates
 * on next access).
 *
 * Auth: NEXT_PUBLIC pages can call this safely — the worst a malicious
 * caller can do is flush the cache for the school detail segment,
 * which is the same as a normal ISR miss. No real damage. Keeping it
 * unauthenticated avoids the cookie / CSRF dance from a client
 * component.
 */

import { NextRequest, NextResponse } from "next/server";
import { revalidatePath } from "next/cache";

const LOCALES = ["en", "ta", "ms"] as const;
const VALID_TYPES = new Set(["school"]);

export async function POST(req: NextRequest) {
  let body: { type?: string; key?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const type = body.type;
  const key = body.key;
  if (!type || !VALID_TYPES.has(type)) {
    return NextResponse.json({ error: "invalid_type" }, { status: 400 });
  }
  if (!key || typeof key !== "string" || !/^[A-Z0-9]{3,10}$/.test(key)) {
    return NextResponse.json({ error: "invalid_key" }, { status: 400 });
  }

  const paths: string[] = [];
  if (type === "school") {
    for (const locale of LOCALES) {
      // 1. The specific bare-code URL the legacy callers use.
      paths.push(`/${locale}/school/${key}`);
      // 2. Sprint 28: invalidate the WHOLE dynamic segment so the
      //    slug URL the user lands on after the 301 also re-renders.
      //    Passing "page" tells Next to revalidate every cached
      //    instance of this dynamic route — every slug for this school
      //    plus any stale prior slug. Heavier but correct.
      paths.push(`/${locale}/school/[moe_code]`);
    }
  }

  for (const p of paths) {
    // Per Next.js docs, calling revalidatePath with a dynamic segment
    // shape needs the second arg `"page"` to invalidate all matching
    // cached instances. Plain string revalidates a single URL.
    if (p.includes("[")) {
      revalidatePath(p, "page");
    } else {
      revalidatePath(p);
    }
  }

  return NextResponse.json({ revalidated: paths });
}
