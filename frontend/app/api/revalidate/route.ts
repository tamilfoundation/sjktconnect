/**
 * Sprint 27 — explicit ISR cache invalidation after admin edits.
 *
 * Problem: `/school/[moe_code]` has `revalidate=86400` so changes a
 * school admin saves don't appear on the public page for up to 24
 * hours. The user reported this twice (Sprint 27 #1 + #4 — Core/Contact
 * tab Save and Leaders tab Save both "succeed" but the public page
 * stays stale).
 *
 * Fix: this route handler accepts a `moe_code` and calls
 * `revalidatePath()` for the school detail page across all 3 locales.
 * SchoolEditForm + LeadersTab call this after a successful save, then
 * navigate to the view page so the user sees the result immediately.
 *
 * Auth: NEXT_PUBLIC pages can call this safely — the worst a malicious
 * caller can do is flush the cache for a specific moe_code, which is
 * the same as a normal ISR miss. No real damage. We keep it
 * unauthenticated to avoid the cookie / CSRF dance from a client
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
      paths.push(`/${locale}/school/${key}`);
    }
  }

  for (const p of paths) {
    revalidatePath(p);
  }

  return NextResponse.json({ revalidated: paths });
}
