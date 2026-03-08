"""Scrape GE15 election results from undi.info API for all constituencies.

Calls https://api.undi.info/election?seat={STATE}.p.{NAME} for each constituency.
Extracts winning margin, total voters, and Indian voter percentage.
Indian voter % comes from GE14 (2018) data if GE15 doesn't have it.

Usage:
    python manage.py scrape_ge15_results                    # Scrape + save to DB
    python manage.py scrape_ge15_results --dry-run          # Preview only
    python manage.py scrape_ge15_results --csv data/ge15.csv  # Also save CSV
"""

import csv
import time

import requests
from django.core.management.base import BaseCommand

from schools.models import Constituency

# Parliament code ranges → undi.info state code
# P001-P003: Perlis, P004-P018: Kedah, P019-P032: Kelantan, P033-P040: Terengganu
# P041-P053: Pulau Pinang, P054-P077: Perak, P078-P091: Pahang
# P092-P113: Selangor, P114-P124: WP KL, P125: WP Putrajaya
# P126-P133: Negeri Sembilan, P134-P139: Melaka, P140-P165: Johor
# P166: WP Labuan, P167-P191: Sabah, P192-P222: Sarawak
CODE_RANGES = [
    (1, 3, "PL"),      # Perlis
    (4, 18, "KD"),     # Kedah
    (19, 32, "KE"),    # Kelantan
    (33, 40, "TR"),    # Terengganu
    (41, 53, "PN"),    # Pulau Pinang
    (54, 77, "PR"),    # Perak
    (78, 91, "PH"),    # Pahang
    (92, 113, "SL"),   # Selangor
    (114, 124, "WP"),  # WP KL
    (125, 125, "WP"),  # WP Putrajaya
    (126, 133, "NS"),  # Negeri Sembilan
    (134, 139, "MK"),  # Melaka
    (140, 165, "JH"),  # Johor
    (166, 166, "LA"),  # WP Labuan
    (167, 191, "SB"),  # Sabah
    (192, 222, "SW"),  # Sarawak
]

# Special name mappings where constituency name doesn't match undi.info seat name
NAME_OVERRIDES = {
    "P018": "KULIM-BANDAR_BAHARU",
}

API_URL = "https://api.undi.info/election"


def get_state_code(parlimen_code):
    """Map constituency code (e.g. 'P075') to undi.info state code."""
    num = int(parlimen_code[1:])
    for start, end, state in CODE_RANGES:
        if start <= num <= end:
            return state
    return None


class Command(BaseCommand):
    help = "Scrape GE15 election results from undi.info API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview without saving to database",
        )
        parser.add_argument(
            "--csv",
            help="Also save results to CSV file",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        csv_path = options.get("csv")
        results = []
        errors = []

        constituencies = Constituency.objects.all().order_by("code")
        total = constituencies.count()

        for i, c in enumerate(constituencies, 1):
            state_code = get_state_code(c.code)
            if not state_code:
                self.stderr.write(f"  [{i}/{total}] SKIP {c.code} {c.name}: no state mapping")
                errors.append(c.code)
                continue

            # Build seat ID: STATE.p.NAME (with underscores, uppercase)
            if c.code in NAME_OVERRIDES:
                seat_name = NAME_OVERRIDES[c.code]
            else:
                seat_name = c.name.upper().replace("'", "")
            seat_id = f"{state_code}.p.{seat_name}"

            try:
                resp = requests.get(API_URL, params={"seat": seat_id}, timeout=10)
                if resp.status_code != 200:
                    self.stderr.write(
                        f"  [{i}/{total}] FAIL {c.code} {c.name}: HTTP {resp.status_code} (seat={seat_id})"
                    )
                    errors.append(c.code)
                    continue

                data = resp.json()
            except Exception as e:
                self.stderr.write(f"  [{i}/{total}] ERROR {c.code}: {e}")
                errors.append(c.code)
                continue

            # Extract GE15 data
            ge15 = data.get("2022-GE", {})
            ge14 = data.get("2018-GE", {})

            if not ge15:
                self.stderr.write(f"  [{i}/{total}] NO GE15 DATA: {c.code} {c.name}")
                errors.append(c.code)
                continue

            # Winning margin: from first candidate's 'majority' field
            candidates = ge15.get("candidates", [])
            margin = candidates[0].get("majority", 0) if candidates else 0
            total_voters = int(ge15.get("info", {}).get("EligibleVoters", 0))

            # Indian voter %: try GE15 first, fall back to GE14
            indian_pct = float(ge15.get("info", {}).get("IndianVoters", 0))
            if indian_pct == 0 and ge14:
                indian_pct = float(ge14.get("info", {}).get("IndianVoters", 0))

            row = {
                "code": c.code,
                "name": c.name,
                "winning_margin": margin,
                "total_voters": total_voters,
                "indian_voter_pct": indian_pct,
            }
            results.append(row)

            if not dry_run:
                c.ge15_winning_margin = margin
                c.ge15_total_voters = total_voters
                c.ge15_indian_voter_pct = indian_pct if indian_pct > 0 else None
                c.save(update_fields=[
                    "ge15_winning_margin",
                    "ge15_total_voters",
                    "ge15_indian_voter_pct",
                ])

            indian_est = int(total_voters * indian_pct / 100) if indian_pct > 0 else 0
            ratio = round(indian_est / margin, 1) if margin > 0 and indian_est > 0 else 0
            self.stdout.write(
                f"  [{i}/{total}] {c.code} {c.name}: "
                f"margin={margin}, voters={total_voters}, "
                f"indian={indian_pct}% ({indian_est}), ratio={ratio}x"
            )

            # Be polite to the API
            time.sleep(0.3)

        # Save CSV if requested
        if csv_path and results:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["code", "name", "winning_margin", "total_voters", "indian_voter_pct"],
                )
                writer.writeheader()
                writer.writerows(results)
            self.stdout.write(f"\nCSV saved to {csv_path}")

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{prefix}Scraped: {len(results)}/{total}, Errors: {len(errors)}"
            )
        )
        if errors:
            self.stderr.write(f"Failed: {', '.join(errors)}")
