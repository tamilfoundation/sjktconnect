# News Digest & Urgent Alert Fix Plan

**Date**: 2026-04-21
**Author**: tamiliam + Claude
**Context**: Investigation of Broadcasts 66–69 revealed two related defects. See conversation on 2026-04-21.

---

## Background

### Defect 1 — Apr 13 News Digest was skipped, Apr 20 covered the wrong window

Expected fortnightly cadence from Broadcast 66 (16–30 Mar, sent 30 Mar):
- **Mon 13 Apr** should have fired a digest covering **31 Mar – 13 Apr**
- **Mon 27 Apr** would be correctly skipped (7-day cooldown)
- **Mon 4 May** fires next

What actually happened:
- **Mon 6 Apr** — correctly skipped (Broadcast 66 within 7 days).
- **Tue 7 Apr** — `send_urgent_alerts` created Broadcast 68 (urgent alert) with `audience_filter={"category": "NEWS_WATCH"}`.
- **Mon 13 Apr** — incorrectly skipped. The digest cooldown query matched Broadcast 68 instead of a prior digest.
- **Mon 20 Apr** — fired, but `_get_since_date` used Broadcast 68's `created_at` as the coverage start, so Broadcast 69 covered **7–20 Apr** instead of starting from the end of Broadcast 66's coverage window (**31 Mar – 20 Apr**).

**Root cause**: `compose_news_digest.py` filters `Broadcast` records by `audience_filter__category="NEWS_WATCH"`. Urgent alerts share that category. The digest composer cannot distinguish a digest from an urgent alert in its own history.

**Secondary bug**: Even in the absence of urgent alerts, `_get_since_date` returns the previous broadcast's `created_at`, not the end of the period it covered. Every digest therefore re-covers the final day of the previous digest.

### Defect 2 — Broadcast 68 should never have been classified as urgent

Article: "Tutup Sekolah Jika Suhu Lebih 37 Selsius 3 Hari Berturut - KPM - Getaran" (Getaran, 27 Mar 2026).

The article is a digest of two announcements from a Deputy Education Minister's visit to SJK(T) Gopeng:
1. **Policy reiteration**: MoE permits headmasters to close schools when temperature exceeds 37°C for three consecutive days. This guideline has existed since 2023; the article simply restates it.
2. **Good news**: SJK(T) Gopeng's 80-year-old termite-damaged building will be demolished and rebuilt under an RM14.5M project starting end-2026, completing in 22 months.

Neither item is a crisis. Nothing demands immediate community action. Yet `news_analyser.py` set `is_urgent=True`, and `send_urgent_alerts.py` auto-sent it to 344 subscribers with a red "URGENT ACTION REQUIRED" banner.

**Root cause**: The urgency criteria in `ANALYSIS_PROMPT` already lists "heat policy announcements" and "dilapidated building repair approvals" as things **not** to flag, but Gemini disregarded those negative examples — likely because keywords like *"tutup sekolah"*, *"anai-anai"*, *"bangunan usang"* pattern-matched against the positive urgency signals more strongly than the negative list. The prompt needs a structural rewrite, not just stronger wording.

**Design intent (clarified by tamiliam)**: Urgent classification should be **rare**. The 30-day `THROTTLE_DAYS` in `send_urgent_alerts.py` is not about preventing email spam — it reflects the expectation that at most ~1 article per month should genuinely qualify. The bug is that the classifier is too permissive, not that the throttle is too loose.

---

## Scope of this plan

Three deliverables:

1. **Digest cadence fix** — separate digest cooldown and coverage calculation from urgent alerts; correct the off-by-one coverage start.
2. **Urgency classifier rewrite** — tighten the Gemini prompt so `is_urgent=True` fires only on true crises; add a second-pass verification.
3. **DRAFT-review safety net for urgent alerts** — build it, but keep it dormant behind a feature flag (`URGENT_ALERT_REQUIRE_REVIEW=false` by default). Flip it on later if another misclassification slips through.

Out of scope:
- Backfilling the 31 Mar – 13 Apr gap. Water under the bridge.
- The off-by-one behaviour of prior digests (Broadcasts 65 and 66 had minor overlap too; not fixing retroactively).
- Article-age cap on urgent alerts (unnecessary once the classifier is correct).

---

## Deliverable 1 — News digest cadence fix

### 1a. Add a `Broadcast.kind` field

`audience_filter` is the wrong place to distinguish broadcast types. It describes *who* receives the broadcast; the *type* of broadcast is orthogonal (e.g., an urgent alert and a digest could both target the NEWS_WATCH audience).

**Migration 0006** (`broadcasts/migrations/0006_broadcast_kind.py`):

```python
class Broadcast(models.Model):
    class Kind(models.TextChoices):
        NEWS_DIGEST = "NEWS_DIGEST", "News Digest"
        URGENT_ALERT = "URGENT_ALERT", "Urgent Alert"
        MONTHLY_BLAST = "MONTHLY_BLAST", "Monthly Blast"
        PARLIAMENT_WATCH = "PARLIAMENT_WATCH", "Parliament Watch"
        OTHER = "OTHER", "Other"

    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.OTHER, db_index=True,
    )
```

**Data migration** (same file, `RunPython`): Populate `kind` on existing rows by inspecting `subject` / `audience_filter`:
- `subject__startswith="URGENT:"` → `URGENT_ALERT`
- `audience_filter__category="MONTHLY_BLAST"` → `MONTHLY_BLAST`
- `audience_filter__category="PARLIAMENT_WATCH"` → `PARLIAMENT_WATCH`
- `audience_filter__category="NEWS_WATCH"` (remainder) → `NEWS_DIGEST`

### 1b. Add `coverage_start_date` and `coverage_end_date` fields

Same migration. Both `DateField(null=True, blank=True)`. Backfill from the subject line parser (`"News Watch — 16 Mar 2026 – 30 Mar 2026"` → start=2026-03-16, end=2026-03-30) for existing digests. Leave null for non-digest rows.

### 1c. Update writers to set `kind` and coverage fields

| Command | File | `kind` | Coverage dates |
|---|---|---|---|
| `compose_news_digest.py` | broadcasts/management/commands | NEWS_DIGEST | start, end |
| `send_urgent_alerts.py` | ditto | URGENT_ALERT | null |
| `compose_urgent_alert.py` | ditto | URGENT_ALERT | null |
| `compose_monthly_blast.py` | ditto | MONTHLY_BLAST | null |
| `compose_parliament_watch.py` | ditto | PARLIAMENT_WATCH | null |
| `views.py` (admin compose) | broadcasts | OTHER (default) | null |

### 1d. Rewrite `_should_skip` and `_get_since_date` in `compose_news_digest.py`

```python
def _get_since_date(self):
    """Start the next digest where the last digest's coverage ended."""
    last = (
        Broadcast.objects.filter(
            kind=Broadcast.Kind.NEWS_DIGEST,
            coverage_end_date__isnull=False,
        )
        .exclude(status=Broadcast.Status.FAILED)
        .order_by("-coverage_end_date")
        .values_list("coverage_end_date", flat=True)
        .first()
    )
    if last:
        return timezone.make_aware(
            datetime.combine(last + timedelta(days=1), time.min)
        )
    return timezone.now() - timedelta(days=14)


def _should_skip(self):
    """Skip if a digest was already created in the last 7 days."""
    return Broadcast.objects.filter(
        kind=Broadcast.Kind.NEWS_DIGEST,
        status__in=[Broadcast.Status.SENT, Broadcast.Status.DRAFT, Broadcast.Status.SENDING],
        created_at__gte=timezone.now() - timedelta(days=7),
    ).exists()
```

Also persist coverage dates on the created Broadcast:

```python
broadcast = Broadcast.objects.create(
    subject=f"News Watch \u2014 {period_label}",
    html_content=html_content,
    text_content=text_content,
    audience_filter={"category": "NEWS_WATCH"},
    kind=Broadcast.Kind.NEWS_DIGEST,
    coverage_start_date=start_date,
    coverage_end_date=end_date,
    status=Broadcast.Status.DRAFT,
)
```

### 1e. Verify next run behaviour

After the fix, with Broadcast 69 having `coverage_end_date=2026-04-20`:
- **Mon 27 Apr** run: `_should_skip` returns True (Broadcast 69 created 20 Apr, ~7d ago at the minute level — same edge-case behaviour as before). Skipped.
- **Mon 4 May** run: `_should_skip` returns False. `_get_since_date` returns `2026-04-21 00:00 MYT`. Coverage: **21 Apr – 4 May 2026**. ✅

### 1f. Tests

Update `backend/broadcasts/tests/test_compose_news_digest.py`:
- Existing urgent-alert in window should NOT trigger skip.
- Existing digest in window SHOULD trigger skip.
- `_get_since_date` returns `coverage_end + 1 day`, not `created_at`.
- Fresh Broadcast has `kind=NEWS_DIGEST` and both coverage dates set.

---

## Deliverable 2 — Urgency classifier rewrite

### 2a. Restructure `ANALYSIS_PROMPT` in `news_analyser.py`

The current single-block prompt buries negative examples. Restructure the urgency section into a two-gate decision:

```text
- is_urgent: Boolean. Decide in two steps.

  STEP 1 — Is there ANY of the following in this article?
    (a) A specific named SJK(T) school confirmed closing/merging in the
        next 30 days, announced in THIS article (not a trend, not a
        historical reference).
    (b) An active emergency at a named SJK(T): building collapse,
        fire, flood damage, mass illness — ongoing right now.
    (c) A government decision announced in THIS article that will
        terminate or restrict SJK(T) operations within 30 days (not
        a general education policy, not a permissive guideline).

  If STEP 1 is "no" for all three, set is_urgent=false and stop.

  STEP 2 — If STEP 1 matched, answer these two questions:
    Q1: Does the community need to ACT in the next 7 days to change
        the outcome? (If the decision is already final and irreversible,
        the answer is no — it's news, not an alert.)
    Q2: Is this the PRIMARY subject of the article, not a passing
        mention or a digression from the main topic?

  Set is_urgent=true only if BOTH Q1 and Q2 are "yes".

  Examples that are NOT urgent (set is_urgent=false):
  - "Heat closure policy permits HMs to shut schools when >37°C."
    (Permissive guideline — HMs gain autonomy, no one needs to act.)
  - "SJK(T) Gopeng to be rebuilt under RM14.5M project."
    (The problem is being solved; this is good news.)
  - "SJK(T) X enrolment dropping for 5th year."
    (Trend, not an event; no 7-day window to act in.)
  - "Ministry visit to SJK(T)."
    (Routine, not an emergency.)
  - "Award controversy involving Tamil school."
    (Advocacy topic, not a crisis.)

  Examples that ARE urgent (set is_urgent=true):
  - "SJK(T) X will close on 1 June; parents have until 15 May to appeal."
    (Named school, 30-day window, actionable deadline, primary subject.)
  - "SJK(T) Y roof collapsed overnight; 200 students displaced."
    (Active emergency, named school.)
  - "Parliament to vote next Tuesday on bill restricting SJK(T) funding."
    (Imminent decision, 7-day action window.)
```

### 2b. Add a second-pass verification

Even with a better prompt, Gemini occasionally ignores its own rules. Add a cheap verification step in `analyse_article`:

```python
def _verify_urgency(article, analysis):
    """Second-pass sanity check when is_urgent=True.

    Sends a narrow verification prompt asking one yes/no question.
    If the second pass disagrees, downgrade to is_urgent=False and log.
    """
    if not analysis["is_urgent"]:
        return analysis

    verify_prompt = VERIFY_URGENT_PROMPT.format(
        title=article.title,
        summary=analysis["summary"],
        reason=analysis["urgent_reason"],
    )
    # Call Gemini with a JSON-mode, 1-key response: {"confirmed": bool, "reason": str}
    # If confirmed=False, log the original reason + verification reason and
    # set is_urgent=False, urgent_reason="".
```

The verification prompt is ~200 tokens and runs only when the first pass says `is_urgent=True`. At the expected rate of ~1 urgent article per 30 days, cost is negligible. Add `urgent_verification_passed` to `ai_raw_response` for audit.

### 2c. Tests

Add `backend/newswatch/tests/test_urgency_classifier.py`:
- Positive fixture: a genuine crisis article → `is_urgent=True`.
- Six negative fixtures from the prompt examples → `is_urgent=False`. Use VCR cassettes or mock the Gemini client.
- Verification step: mock a first-pass `is_urgent=True` + second-pass `confirmed=False` → final `is_urgent=False`.

### 2d. One-off cleanup

After deploying, run:
```bash
python manage.py shell -c "
from newswatch.models import NewsArticle
stale = NewsArticle.objects.filter(is_urgent=True, review_status='APPROVED')
print(f'Stale urgent articles: {stale.count()}')
# Clear the flag on articles older than 30 days that never triggered an alert
# (Broadcast 68 already triggered; these are all older mis-classifications)
stale.filter(published_date__lt=timezone.now() - timedelta(days=30)).update(is_urgent=False, urgent_reason='')
"
```

---

## Deliverable 3 — DRAFT-review safety net (built but dormant)

### 3a. Feature flag

Add to `backend/sjktconnect/settings.py`:

```python
URGENT_ALERT_REQUIRE_REVIEW = os.environ.get(
    "URGENT_ALERT_REQUIRE_REVIEW", "false"
).lower() == "true"
```

Default `false` everywhere (dev, prod). No Cloud Run env var changes needed unless we flip it on.

### 3b. Branch in `send_urgent_alerts.py`

```python
broadcast = Broadcast.objects.create(
    subject=f"URGENT: {article.title}",
    html_content=html_content,
    text_content=strip_tags(html_content),
    audience_filter={
        "category": "NEWS_WATCH",
        "subscribed_before": article.created_at.isoformat(),
    },
    kind=Broadcast.Kind.URGENT_ALERT,
    status=Broadcast.Status.DRAFT,
)

if settings.URGENT_ALERT_REQUIRE_REVIEW:
    self.stdout.write(
        self.style.WARNING(
            f"  Broadcast {broadcast.pk} created as DRAFT for review. "
            f"Flag URGENT_ALERT_REQUIRE_REVIEW=true is set. "
            f"Approve via admin to send."
        )
    )
    # TODO: trigger notification email to admin@ — deferred until flag flips
    continue

send_broadcast(broadcast.pk)
```

### 3c. Admin approve/reject UI

Already exists for `compose_news_digest` (admin moderator queue). Add a filter to list `kind=URGENT_ALERT, status=DRAFT` broadcasts at `/admin/broadcasts/` and surface them in the existing dashboard. Button: "Send now" (calls `send_broadcast`) and "Reject" (sets `status=FAILED`).

### 3d. Tests

- With flag=False: broadcast is created AND sent (current behaviour).
- With flag=True: broadcast is created as DRAFT, `send_broadcast` is not called.
- Admin approve endpoint transitions DRAFT → SENT via `send_broadcast`.

### 3e. How to activate later

If another misclassification slips through:

```bash
gcloud run jobs update sjktconnect-urgent-alerts \
  --region=asia-southeast1 \
  --project=sjktconnect \
  --account=admin@tamilfoundation.org \
  --update-env-vars=URGENT_ALERT_REQUIRE_REVIEW=true
```

No redeploy needed.

---

## Risks & considerations

1. **Migration timing.** The `kind` field backfill runs on existing ~69 broadcasts — small, safe. Coverage-date backfill parses subject lines with a regex; test against Broadcasts 65, 66, 69 locally before deploying.

2. **Urgent alert false-negatives.** A stricter classifier may miss a real crisis. The 30-day throttle on `send_urgent_alerts` means we only send ~1/month even when multiple articles qualify, so the cost of a false-negative is bounded — the digest will still cover it fortnightly. Acceptable trade-off.

3. **Verification double-spend.** The two-pass urgency check doubles Gemini calls on urgent-flagged articles only. At ~1 urgent article per month, negligible.

4. **Dormant feature flag drift.** Deliverable 3's code path stays untested in prod until we flip the flag. Mitigation: unit tests cover both branches; if the flag flips, a single manual end-to-end test before the next urgent alert is enough.

5. **Existing Broadcasts 65–68.** The migration sets `kind` and, for digests, `coverage_start_date`/`coverage_end_date`. Broadcast 68 (urgent alert) gets `kind=URGENT_ALERT` and null coverage. Broadcast 69 gets `coverage_start=2026-04-07, coverage_end=2026-04-20` — the actual window it covered, even though it was wrong. We do not rewrite history.

---

## Rollout order

1. Migration 0006 (`kind`, coverage dates, backfill) → deploy, verify existing rows populated.
2. Update all 5 writers to set `kind` and (for digests) coverage dates.
3. Rewrite `_should_skip` / `_get_since_date` + tests.
4. Rewrite urgency prompt + add verification pass + tests.
5. Build feature-flagged DRAFT-review path + tests (flag stays off).
6. Deploy.
7. Manual verification on 4 May cron run.

---

## Acceptance criteria

- [ ] `Broadcast.kind` field exists with `NEWS_DIGEST`, `URGENT_ALERT`, `MONTHLY_BLAST`, `PARLIAMENT_WATCH`, `OTHER`.
- [ ] `Broadcast.coverage_start_date` and `coverage_end_date` fields exist.
- [ ] All 5 writers set `kind` correctly; digest writer also sets coverage dates.
- [ ] Existing broadcasts 1–69 have `kind` populated; digests have coverage dates.
- [ ] A unit test proves urgent alerts do NOT trigger digest cooldown skip.
- [ ] A unit test proves `_get_since_date` returns `coverage_end + 1 day`, not `created_at`.
- [ ] Urgency classifier test suite: 1 positive + 6 negative fixtures all pass.
- [ ] Second-pass verification: first-pass True + second-pass False → final False.
- [ ] `URGENT_ALERT_REQUIRE_REVIEW=false` preserves current auto-send behaviour.
- [ ] `URGENT_ALERT_REQUIRE_REVIEW=true` leaves broadcast as DRAFT and exits without sending.
- [ ] 4 May 2026 digest fires with coverage "21 Apr – 4 May 2026".
