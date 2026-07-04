# Management Commands Catalogue

A quick reference so a future engineer (or my future self) can tell at a glance which `python manage.py <cmd>` invocations are still driven by schedulers vs which were one-off backfills for a specific sprint.

Written 2026-07-01 as the second half of the audit-follow-up cosmetic tidy-up. The audit's original suggestion — move historical commands under `backend/scripts/one-shots/` — would break Django's command discovery (only files under `<app>/management/commands/` are picked up by `manage.py`). This catalogue is the safer alternative.

## Runtime commands (driven by Cloud Run Jobs / Scheduler)

Wired via [backend/scripts/update_jobs.sh](../backend/scripts/update_jobs.sh). Whoever changes any of these must re-verify the corresponding Cloud Run Job manifest after backend deploy.

| Command | Cloud Run Job | Cadence |
| --- | --- | --- |
| `run_hansard_pipeline` | `sjktconnect-check-hansards` | Daily 08:00 MYT |
| `run_news_pipeline` | `sjktconnect-news-pipeline` | Daily 08:30 MYT |
| `send_urgent_alerts` | `sjktconnect-urgent-alerts` | Daily 09:30 MYT |
| `compose_news_digest` | `sjktconnect-news-digest` | Weekly (14-day coverage window) |
| `compose_monthly_blast` | `sjktconnect-monthly-blast` | 1st of month, 09:00 MYT |
| `resume_sending` | `sjktconnect-resume-sending` | Daily 10:00 MYT |
| `process_feedback` | `sjktconnect-process-feedback` | 8AM/12PM/4PM/8PM MYT daily |
| `janitor_orphan_images` | `sjktconnect-janitor-orphan-images` (Sprint 33, awaiting creation) | Weekly Sun 03:00 MYT (proposed) |

## Runtime-callable but not scheduled

Invoked by owner on demand — kept runtime-callable (do not delete).

| Command | Owner invocation |
| --- | --- |
| `rematch_schools` | After every SchoolAlias migration (used 2× on 2026-06-29 alone). |
| `seed_aliases`, `seed_aliases --clear` | After alias-generator changes; re-materialises variants for all 528 schools. |
| `check_new_hansards`, `process_hansard <url>` | Manual Hansard investigation. |
| `import_bank_details` | After a new TF bank-details Excel export. |
| `import_mp_profiles` | After parlimen.gov.my scraper changes. |
| `import_constituencies`, `import_schools` | After MOE data refresh (Jan/Apr/Sep releases). |
| `import_enrolment_snapshots` | When a new MOE Risalah file lands. |
| `send_broadcast --test-recipients <email>` | Send a test email to owner before releasing a broadcast to the list. |
| `analyse_mentions`, `update_scorecards`, `harvest_school_images`, `send_outreach_emails` | Ad-hoc pipeline steps. |
| `compose_parliament_watch`, `compose_urgent_alert` | Manually compose a broadcast draft when the scheduled paths are paused. |
| `analyse_news_articles`, `extract_articles`, `fetch_news_alerts` | Individual news-pipeline stages when troubleshooting. |
| `verify_school_pins` | GPS reconciliation with Google Places — expensive (Google API cost). |
| `migrate_images_to_storage` | Sprint-13-era Supabase Storage backfill. Should be idempotent; safe to re-run in a pinch. |

## Historical one-shots (safe to leave, do not delete)

These ran once for a specific migration/backfill and haven't been invoked since. They stay in-tree so their SQL/logic is auditable, but no cron or workflow triggers them.

| Command | Sprint | Purpose |
| --- | --- | --- |
| `rebuild_all_hansards` | 5.2 / Full Rebuild | Wipe + reprocess all 15th Parliament Hansard PDFs. |
| `backfill_mp_names` | 5.3 | Backfill `HansardMention.mp_name` after the MP scraper landed. |
| `backfill_speakers` | 5.2 | Re-run speaker extraction with the improved 2-page lookback. |
| `backfill_news` | 2.6 | Backfill AI analysis on legacy `NewsArticle` rows. |
| `reclassify_existing_articles` | 24 (10a) | Re-run Gemini triage after DOMAIN_BLOCKLIST + prompt tweak. |
| `clear_stale_urgent_flags` | Urgent-alert cleanup | Reset stuck `is_urgent=True` from before the two-gate rewrite. |
| `scrape_ge15_results` | 5.4 | Pull GE15 tallies from undi.info. Rerun only for future elections. |
| `seed_school_histories` | 31 / 31.1 | Bulk-load Wikipedia-sourced school histories. Re-runnable when Wikipedia coverage grows. |
| `relabel_labu_mistags` | 28.1 | One-off relabelling of 7 news articles mis-tagged to non-Labu schools. |
| `import_ge15_results` | 5.4 CSV fallback | CSV import fallback for the same GE15 pull. |
| `import_subscribers_from_text` | 2.4 (owner import) | Bulk-import subscribers from a text list. |
| `import_stitch_screens` | (if present) | Ad-hoc Stitch-mockup ingest. |

## When to add a new command

Runtime → wire into `update_jobs.sh` + Cloud Scheduler in the same commit.
One-shot → run it locally against prod (with `SJKTCONNECT_ALLOW_PROD_DB=1`) and record here at sprint close.
