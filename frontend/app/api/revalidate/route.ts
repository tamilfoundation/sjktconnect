/**
 * Server-driven ISR cache invalidation after admin edits.
 *
 * Originally Sprint 27 (route handler) and Sprint 28 (slug fix). TD-21
 * (audit 2026-06-26) added the auth gate: previous design was an
 * unauthenticated POST callable from the browser. That was a DoS
 * amplifier — a scripted attacker at 10 req/s triggered 60 ISR
 * regenerations/s, each running a full SchoolDetailPage + Django API +
 * Supabase fetch. With two prior egress incidents in project history,
 * leaving that surface open was the wrong default.
 *
 * Now requires `X-Revalidate-Token` header matching `REVALIDATE_TOKEN`
 * env var (set on Cloud Run for both api + web). The Django backend
 * fires the POST after a successful school/leader edit
 * (`schools/services/revalidation.py`). The browser no longer calls
 * this endpoint.
 *
 * What we revalidate: bare-code URL `/{locale}/school/{key}` (legacy
 * inbound links that 301 to the slug) AND the literal slug URL
 * `/{locale}/school/{slug}` (the canonical, what users actually land
 * on). The dynamic-segment form `revalidatePath('...', 'page')` does
 * NOT invalidate the specific cached slug instance in our setup
 * (verified live 2026-06-26 — Sprint 28.1 lesson). Passing the
 * literal slug is the only thing that actually busts it.
 */

import { NextRequest, NextResponse } from "next/server";
import { revalidatePath } from "next/cache";

const LOCALES = ["en", "ta", "ms"] as const;
const VALID_TYPES = new Set(["school", "parliament"]);

export async function POST(req: NextRequest) {
  // TD-21 auth gate. Env var must be set on Cloud Run for prod
  // revalidation to work; if unset locally, every request is 503.
  const expected = process.env.REVALIDATE_TOKEN?.trim();
  if (!expected) {
    return NextResponse.json(
      { error: "revalidate_disabled" },
      { status: 503 },
    );
  }
  const provided = req.headers.get("x-revalidate-token")?.trim();
  if (!provided || provided !== expected) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: { type?: string; key?: string; slug?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const type = body.type;
  const key = body.key;
  const slug = body.slug;
  if (!type || !VALID_TYPES.has(type)) {
    return NextResponse.json({ error: "invalid_type" }, { status: 400 });
  }
  if (type === "school") {
    if (!key || typeof key !== "string" || !/^[A-Z0-9]{3,10}$/.test(key)) {
      return NextResponse.json({ error: "invalid_key" }, { status: 400 });
    }
    // Slug is optional but validated when present — same alphabet as
    // schoolPath() output (lowercase letters, digits, hyphens).
    if (slug !== undefined && (typeof slug !== "string" || !/^[a-z0-9-]{3,200}$/.test(slug))) {
      return NextResponse.json({ error: "invalid_slug" }, { status: 400 });
    }
  } else if (type === "parliament") {
    // key = numeric SittingBrief id, optional. When present we also bust
    // that brief's detail page; the two list pages are always refreshed.
    if (key !== undefined && (typeof key !== "string" || !/^[0-9]{1,7}$/.test(key))) {
      return NextResponse.json({ error: "invalid_key" }, { status: 400 });
    }
  }

  const paths: string[] = [];
  if (type === "school") {
    for (const locale of LOCALES) {
      // Bare-code URL — what legacy inbound links point at; 301s to slug.
      paths.push(`/${locale}/school/${key}`);
      // Slug URL — the canonical, what users actually land on. The
      // dynamic-segment form (`/[locale]/school/[moe_code]`) does NOT
      // invalidate the specific cached slug instance in our setup
      // (verified live 2026-06-26 — revalidate returned the expected
      // path list, but the slug URL kept serving stale data). Passing
      // the literal slug is the only thing that actually busts it.
      if (slug) {
        paths.push(`/${locale}/school/${slug}`);
      }
    }
  } else if (type === "parliament") {
    // A published sitting brief must surface on both cached list pages
    // (home + full list); include the brief's own detail page when a
    // numeric id is supplied. These are static/literal routes, so
    // revalidatePath busts them directly (no dynamic-segment caveat).
    for (const locale of LOCALES) {
      paths.push(`/${locale}/parliament-watch`);
      paths.push(`/${locale}/parliament-watch/sittings`);
      if (key) {
        paths.push(`/${locale}/parliament-watch/sittings/${key}`);
      }
    }
  }

  for (const p of paths) {
    revalidatePath(p);
  }

  return NextResponse.json({ revalidated: paths });
}
