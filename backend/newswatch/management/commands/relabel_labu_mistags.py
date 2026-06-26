"""Re-tag the 7 articles about SJK(T) Ladang Labu Bhg 4 (NBD4079)
that were mis-resolved to ABDB006 / MBD0067.

Background (Sprint 27 + 28):
  - News matcher Strategy 5 fell back to single-token `icontains` on
    `short_name`. Articles saying "SJKT Ladang Labu Bahagian/Division 4"
    landed on the only schools in the DB with those tokens —
    ABDB006 ("Jendarata Bahagian Alpha Bernam") and MBD0067 ("Kemuning
    Kru Division").
  - First-resolution permanently OVERWRITES `mentioned_schools[i].name`
    with the matched school's `short_name`. So the stored name is now
    the WRONG school's name, and `rematch_schools --force-all` just
    re-resolves to the same wrong school. The original Gemini-extracted
    "SJKT Ladang Labu Bahagian 4" string is lost.
  - Sprint 28's seed_aliases extension closes the gap for FUTURE
    articles via Strategy 1.5. This command cleans up the existing 7.

Approach: find articles where the published title contains "Labu" AND
mentioned_schools[*].moe_code is in {ABDB006, MBD0067}, and rewrite
the mention to NBD4079. Idempotent. --dry-run shows the plan.
"""

from django.core.management.base import BaseCommand

from newswatch.models import NewsArticle


_WRONG_CODES = {"ABDB006", "MBD0067"}
_RIGHT_CODE = "NBD4079"
_RIGHT_NAME = "SJK(T) Ladang Labu Bhg 4"


class Command(BaseCommand):
    help = "Re-tag Labu Bhg 4 articles mis-resolved to ABDB006/MBD0067."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Articles whose TITLE mentions Labu (case-insensitive) — these
        # are the only candidates. Avoids touching legit ABDB006/MBD0067
        # coverage.
        articles = NewsArticle.objects.filter(
            title__icontains="Labu",
        ).exclude(mentioned_schools=[])

        updated = unchanged = 0
        for article in articles:
            new_mentions = []
            changed = False
            for m in article.mentioned_schools or []:
                code = (m or {}).get("moe_code")
                if code in _WRONG_CODES:
                    new_mentions.append(
                        {"name": _RIGHT_NAME, "moe_code": _RIGHT_CODE}
                    )
                    changed = True
                else:
                    new_mentions.append(m)
            if not changed:
                unchanged += 1
                continue
            self.stdout.write(
                f"Article {article.pk}: {article.title[:75]}"
            )
            for old, new in zip(article.mentioned_schools, new_mentions):
                if old != new:
                    self.stdout.write(
                        f"  {old.get('moe_code'):>8} -> {new.get('moe_code'):>8}"
                    )
            if not dry_run:
                article.mentioned_schools = new_mentions
                article.save(update_fields=["mentioned_schools"])
            updated += 1

        verb = "would update" if dry_run else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {updated} articles, {unchanged} already correct."
            )
        )
