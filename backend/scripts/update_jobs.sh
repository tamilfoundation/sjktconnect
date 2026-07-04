#!/usr/bin/env bash
#
# Update every Cloud Run job to use the image currently serving 100% traffic
# on the sjktconnect-api service. Run after every backend deploy.
#
# Why this exists:
#   Cloud Run Jobs carry their own pinned image, separate from the api
#   service. They don't auto-update when the service is redeployed, so any
#   migration that drops a column, renames a model field, or changes
#   imported modules will make jobs running stale images crash silently
#   on their next scheduled run.
#
#   The 2026-05-20 incident — 21 days of silent rot in the news pipeline —
#   was caused exactly this way: Sprint 19 dropped schools_school.last_verified
#   on 28 April; jobs kept running the pre-Sprint-19 image; every daily run
#   crashed with ProgrammingError; nobody noticed because there was no
#   alerting and the digest skipped gracefully on zero approved articles.
#
# Usage:
#   ./scripts/update_jobs.sh              # update all jobs
#   ./scripts/update_jobs.sh --dry-run    # show what would change, don't apply
#
# Prerequisites:
#   gcloud authenticated as admin@tamilfoundation.org with run.developer role
#   on the sjktconnect project.

set -euo pipefail

PROJECT=sjktconnect
ACCOUNT=admin@tamilfoundation.org
REGION=asia-southeast1
SERVICE=sjktconnect-api

JOBS=(
  sjktconnect-news-pipeline
  sjktconnect-news-digest
  sjktconnect-urgent-alerts
  sjktconnect-monthly-blast
  sjktconnect-resume-sending
  sjktconnect-process-feedback
  sjktconnect-check-hansards
  sjktconnect-janitor-orphan-images
)

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

echo "Reading current image from service $SERVICE..."
CURRENT_IMAGE=$(gcloud run services describe "$SERVICE" \
  --project="$PROJECT" --account="$ACCOUNT" --region="$REGION" \
  --format="value(spec.template.spec.containers[0].image)")

if [[ -z "$CURRENT_IMAGE" ]]; then
  echo "ERROR: could not read image from $SERVICE" >&2
  exit 1
fi

echo "Target image: $CURRENT_IMAGE"
echo

UPDATED=0
SKIPPED=0
MISSING=0

for job in "${JOBS[@]}"; do
  JOB_IMAGE=$(gcloud run jobs describe "$job" \
    --project="$PROJECT" --account="$ACCOUNT" --region="$REGION" \
    --format="value(spec.template.spec.template.spec.containers[0].image)" \
    2>/dev/null || echo "")

  if [[ -z "$JOB_IMAGE" ]]; then
    echo "  $job: NOT FOUND (skipping)"
    MISSING=$((MISSING + 1))
    continue
  fi

  if [[ "$JOB_IMAGE" == "$CURRENT_IMAGE" ]]; then
    echo "  $job: already current"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  $job: WOULD update"
    echo "    from: $JOB_IMAGE"
    echo "    to:   $CURRENT_IMAGE"
    continue
  fi

  echo "  $job: updating..."
  gcloud run jobs update "$job" \
    --project="$PROJECT" --account="$ACCOUNT" --region="$REGION" \
    --image="$CURRENT_IMAGE" >/dev/null
  echo "  $job: done"
  UPDATED=$((UPDATED + 1))
done

echo
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry-run complete."
else
  echo "Updated: $UPDATED  Already current: $SKIPPED  Missing: $MISSING"
fi
