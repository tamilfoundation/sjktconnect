"""Import GE15 election results from a CSV file into Constituency model.

CSV format: code,winning_margin,total_voters,indian_voter_pct
Example:    P.075,348,58183,22.0

Usage:
    python manage.py import_ge15_results data/ge15_results.csv
    python manage.py import_ge15_results data/ge15_results.csv --dry-run
"""

import csv

from django.core.management.base import BaseCommand

from schools.models import Constituency


class Command(BaseCommand):
    help = "Import GE15 election results from CSV into Constituency model"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to CSV file with GE15 data")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to database",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        updated = 0
        skipped = 0
        not_found = 0

        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_code = row["code"].strip()
                # Normalise code: "P.075" → "P075", "P075" stays "P075"
                code = raw_code.replace(".", "")

                try:
                    c = Constituency.objects.get(code=code)
                except Constituency.DoesNotExist:
                    self.stderr.write(f"  NOT FOUND: {raw_code} → {code}")
                    not_found += 1
                    continue

                margin = int(row["winning_margin"].strip())
                voters = int(row["total_voters"].strip())
                indian_pct = float(row["indian_voter_pct"].strip())

                if dry_run:
                    indian_est = int(voters * indian_pct / 100)
                    ratio = round(indian_est / margin, 1) if margin > 0 else 0
                    self.stdout.write(
                        f"  {code} {c.name}: margin={margin}, voters={voters}, "
                        f"indian={indian_pct}% ({indian_est}), ratio={ratio}x"
                    )
                else:
                    c.ge15_winning_margin = margin
                    c.ge15_total_voters = voters
                    c.ge15_indian_voter_pct = indian_pct
                    c.save(update_fields=[
                        "ge15_winning_margin",
                        "ge15_total_voters",
                        "ge15_indian_voter_pct",
                    ])
                updated += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Updated: {updated}, Skipped: {skipped}, Not found: {not_found}"
            )
        )
