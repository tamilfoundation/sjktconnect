# Sprint 35 Retrospective — Monthly Blast Quality Overhaul

**Duration**: ~1 working day, 2026-07-04 → 2026-07-05
**Commits**: 11
**Deploys**: 3 backend (api-00147-vtr chain → api-00159-nlw), 0 frontend
**Tests**: 346 → 357 broadcast tests (+11)

## What Was Built

A single-surface quality sweep on the monthly intelligence blast — no new features, no new pipelines. The June 2026 blast landed in owner's Gmail with three real reader problems that the audit had missed (the audit checked security / perf / correctness — reader experience of a rendered email in Android Gmail wasn't a lens it applied). Sprint 35 fixed those, then took the chance to align the template with the site's brand palette + hero button pattern, and closed two link-quality issues that were quietly costing us clicks and analytics attribution.

Owner-visible changes:

1. Mobile-responsive layout at 320-400 px (headline, stat bar, schools list).
2. No story reuse across analytical sections (Executive Summary / Trend Lines / Opportunity Watch / School Spotlight all cover different angles; Emerging Signals + Fading From View retired).
3. Analyst top-story now matches news card #1 (cluster-first ordering + analyst-picks-cluster contract + `_promote_top_story` pin).
4. Navy brand palette across all bulk email templates (30 refs of `#7c3aed` violet → `#2563eb`).
5. By The Numbers + Take Action + Footer flipped to whole-panel navy `#1e3a8a` with white/light-blue text.
6. Take Action buttons match site hero pattern (1 solid white primary + 2 outlined white-on-navy secondaries).
7. Letterhead-style header (wordmark on left, bold month/year on right, H1 title below).
8. School links in newsletter now use canonical `/en/school/<name>-<city>-<moe-lc>` slug (was legacy bare-code + 301 through Cloudflare).
9. MP mentions like `(P148 Ayer Hitam)` in analyst prose now hyperlink to the constituency page.

## What Went Well

- **Ship-preview-fix loop tightened.** Every visual change went through: edit template → `--preview-html` render → Artifact upload → owner eyeballs → iterate. No blind deploys. Preview URLs stayed stable via the `label` param so the version picker showed the delta cleanly (v4 → v10).
- **Owner corrections were tight and testable.** "Violet is not our colour" → 30-ref sweep. "The buttons are ugly" → concrete reference image → clear pattern to copy. "I meant the entire section, not just the buttons" → obvious next iteration. No ambiguity, no rework.
- **The linkifier + slug-tag pairs were symmetric.** Both landed as a single-file templatetag module + a filter/tag + tests + a template edit + a small template comment noting *why the change exists*. Predictable to review, obvious to test.
- **Test-first paid off on the coherence fix.** `_promote_top_story` had a pytest-collection false start (class named `PromoteTopStoryTest` instead of `TestPromoteTopStory`) — caught immediately because the test was written before the deploy. If the check had been visual-only, the bug would have shipped.

## What Went Wrong

### 1. Django `{# ... #}` multi-line comment leaked through the template three separate times

**Symptom**: A multi-line comment intended for future readers rendered as literal text under Schools In The Spotlight in the preview HTML, then in the send preview, then again after an unrelated edit — three distinct occurrences in this sprint alone.

**Root cause**: Django's `{# ... #}` comment tag is **single-line only**. The template parser sees an unclosed `{#`, treats the whole block as raw text, and — because the comment was inside a `{% for %}` loop — renders it once per iteration. This is documented behaviour but easy to forget when writing HTML that lives among lots of `{% %}` blocks.

**System change**: Added to `docs/lessons.md` as a load-bearing template rule. Any comment longer than one line in a Django template must use `{% comment %} … {% endcomment %}` or, if it's outside all `{% %}` blocks, HTML `<!-- -->`. Also flagged: the `test_render_has_no_unescaped_em_dash` test (Sprint 24) does *not* catch this because em-dashes don't appear in typical comment prose — the leaked comment slips past the anti-unicode gate. Not adding a test for this because the fix is a discipline rule; the test would need to render every template with a comment in every possible position, which isn't worth the code.

### 2. Em-dashes in code comments kept tripping `test_render_has_no_unescaped_em_dash`

**Symptom**: Multiple edits to the template's HTML comments (which I was actively rewriting to fix issue #1 above) triggered the Sprint 24 anti-Unicode test to fail because the em-dashes I used for readability in the comment text ended up in the rendered HTML.

**Root cause**: I write em-dashes reflexively in explanatory prose. The Sprint 24 test blocks *any* em-dash in rendered output because Gmail was corrupting them; it doesn't care whether the em-dash is in copy or in a comment.

**System change**: Note to self (added to `docs/lessons.md`) — template code-comments must use ASCII `--` not `—`. Not worth a lint rule; the test already catches it. The improvement is: when the test fails, look at rendered *comments* too, not just body copy.

### 3. Brevo IP allowlist blocked me from sending test emails to myself

**Symptom**: Wanted to verify the mobile layout in real Gmail before deploy. `send_test` mgmt command 401'd because my home IP isn't on the Brevo allowlist.

**Root cause**: Brevo requires IP allowlisting for API sends. My personal IP is not on it; only the Cloud Run egress ranges are.

**System change**: None warranted for now — the Artifact preview URL is a good enough proxy for Gmail rendering (Gmail is one of Artifact's supported preview surfaces). If mobile-specific bugs ever survive the Artifact preview, we revisit and either allowlist my IP or add a dev-mode SMTP tunnel. Deferred until the first regression.

### 4. GCP alert-policy design detour

**Symptom**: Spent >1 h building the Cloud Monitoring egress-alert policy — DISTRIBUTION metric couldn't be sum-aggregated with GCP's filter syntax; MQL policies only allow a single condition; MQL 24 h query limit rejected `align delta(1d)`.

**Root cause**: Kept trying the "obvious" MQL shape (24 h delta, two conditions ORed) before reading the constraint docs.

**System change**: This was actually resolved in the previous sprint (34) as part of the audit follow-up, not in Sprint 35 — noting here for retrospective completeness. Fix landed: single-condition MQL, `align delta(6h)` at 200 MB threshold = 800 MB/day sustained equivalent.

## Design Decisions

### Cluster news first, then let the analyst pick the top story

**Decision**: In `compose_monthly_blast`, cluster the news articles into hybrid-scored groups *before* calling `generate_monthly_analysis`. Pass the resulting `news_clusters` list to the analyst as context. The analyst returns a `top_story_cluster_index` field identifying which cluster it chose as the "top story" for its Executive Summary. Post-generation, `_promote_top_story()` pins that cluster to position 0 in the rendered news list.

**Alternatives considered**:
- Let the analyst generate its own free-text top story, then post-hoc match it to a news cluster via keyword similarity. Rejected: fragile (match quality varies with headline style); the analyst may name schools that no news cluster centres on; adds a fuzzy-match layer we'd have to test.
- Rank news clusters by hybrid score, hard-pick #1 as the top story, and constrain the analyst to write about *that* cluster. Rejected: the highest-scoring cluster isn't always the most *analytically* interesting one (score prioritises freshness + article count). Analyst judgment is genuinely additive here.

**Rationale**: The chosen approach preserves analyst judgment on *which* cluster is worth spotlighting, and lets deterministic code enforce that the reader sees that cluster first. It also gives us a single source of truth (the cluster index) that both the analyst prompt and the render can agree on — no fuzzy matching, no free-text.

**Trade-offs**: Gemini has to be told the cluster metadata format and asked to pick an index — one more prompt constraint to maintain. If the analyst returns an invalid index, `_promote_top_story` no-ops and the news list retains hybrid-score order.

**Revisit if**: The analyst starts consistently picking `top_story_cluster_index=None` (i.e. it can't confidently pick), which would suggest either the prompt is too strict or the cluster metadata isn't informative enough.

### Post-process linkification, not analyst-generated markup

**Decision**: Turn `(P### Constituency)` mentions into hyperlinks via a Django template filter (`{{ text|linkify_mps }}`) that regex-substitutes at render time. The analyst prompt is unchanged — it produces plain prose, and the template does the linkification.

**Alternatives considered**:
- Ask Gemini to emit `[Ayer Hitam](https://tamilschool.org/...)` markdown in the prose. Rejected: adds prompt complexity + a markdown → HTML pass; every hallucination becomes a broken link; harder to test the analyst output shape.
- Structure the analyst output as JSON with a separate "mentioned_constituencies" list, and render inline. Rejected: over-engineering for a stylistic touch; would require restructuring the entire analyst return shape.

**Rationale**: The filter is <30 lines, verifies each `P###` against the actual `Constituency` table before linking (so hallucinated codes stay text — never a broken link in an inbox), and is trivially testable. The analyst prompt stays focused on writing good prose.

**Trade-offs**: If the analyst starts using a different citation style (e.g. `MP Wee Ka Siong of Ayer Hitam`), the filter won't catch it. Acceptable — the audit example is the pattern Gemini has produced consistently across the last 4 blasts.

**Revisit if**: Gemini's prose style drifts to a citation shape the filter doesn't recognise for 2+ months running; then either update the regex or move to a structured emit.

### Whole-panel navy for Take Action + Footer, not just buttons

**Decision**: When owner said "the buttons look wrong", the fix wasn't to restyle the buttons in isolation but to extend the navy panel to the entire Take Action section header + button row + into the footer.

**Alternatives considered**:
- Just restyle buttons to look like the site hero pattern (1 solid + 2 outlined). Owner explicitly redirected: "I meant the entire Take action section, and not just the buttons."
- Navy button colours on white background. Rejected: buttons ended up looking flat and disconnected; the site's hero has the buttons *on* a coloured band, and that's what gives them visual weight.

**Rationale**: One continuous navy band from By The Numbers → Take Action → Footer reads as a deliberate visual anchor at the bottom of the email. It also frames the actions (donate / forward / your MP) as the "call to action" moment rather than one more content block.

**Trade-offs**: Adds ~20 % more "dark" area to the email, which some readers might find heavier. Acceptable given the site precedent + the owner's explicit direction. Also: harder to iterate on the footer copy without disturbing the panel border.

**Revisit if**: Open rate or click-through on Take Action buttons drops after Aug 1 blast lands, vs the June 2026 baseline.

## Numbers

- **Commits**: 11
- **Tests**: 346 → 357 broadcast (+11)
- **Full backend suite**: 1519 (broadcast +11; pre-Sprint-35 baseline was reported as 1497 in the Sprint 34 close, delta reconciled at Sprint 35 close pytest --collect-only)
- **Frontend suite**: 366 collected, 1 test + 2 suites pre-existing failures inherited from Sprint 31/32
- **LOC**: +153 / -8 in the last commit (linkify_mps) + comparable across earlier commits
- **Deploys**: 3 backend chained (api-00147 → 00149 → ... → 00159), 0 frontend, 3 job-sync runs
- **Prod state at close**: api `sjktconnect-api-00159-nlw`, web `sjktconnect-web-00182-n2d`
- **Time-to-fire (Aug 1 blast)**: 27 days
- **Wall-clock**: ~1 working day of active engagement across 2 calendar days
