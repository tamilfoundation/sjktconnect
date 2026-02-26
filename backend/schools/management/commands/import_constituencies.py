"""
Import constituency and DUN data from Political Constituencies CSV.

Usage:
    python manage.py import_constituencies
    python manage.py import_constituencies --dry-run
    python manage.py import_constituencies --file /path/to/file.csv
"""

import csv
import logging
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from schools.models import Constituency, DUN

logger = logging.getLogger(__name__)

# Default CSV path: two levels up from backend/
DEFAULT_CSV = Path(__file__).resolve().parent.parent.parent.parent.parent / "Political Constituencies.csv"


def parse_code_name(value):
    """Parse 'P140 Segamat' or 'N01 Buloh Kasap' into (code, name)."""
    if not value or not value.strip():
        return None, None
    value = value.strip()
    match = re.match(r"^([A-Z]\d+)\s+(.+)$", value)
    if match:
        return match.group(1), match.group(2).strip()
    return None, value


def parse_income(value):
    """Parse 'RM6,399' or ' RM6,399 ' into integer 6399."""
    if not value or not value.strip():
        return None
    cleaned = re.sub(r"[^\d]", "", value.strip())
    return int(cleaned) if cleaned else None


def parse_decimal(value):
    """Parse '3.4' or '0.304' into float, handling empty strings."""
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def parse_integer(value):
    """Parse integer, handling commas and empty strings."""
    if not value or not value.strip():
        return None
    cleaned = re.sub(r"[^\d]", "", value.strip())
    return int(cleaned) if cleaned else None


def parse_indian_percentage(value):
    """Parse '5.01 - 10%' range into midpoint, or direct percentage."""
    if not value or not value.strip():
        return None
    value = value.strip().rstrip("%")
    # Range format: "5.01 - 10"
    range_match = re.match(r"([\d.]+)\s*-\s*([\d.]+)", value)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        return round((low + high) / 2, 2)
    # Direct percentage
    try:
        return float(value)
    except ValueError:
        return None


def clean_party(value):
    """Clean party string, removing BOM/special chars."""
    if not value:
        return ""
    # Remove non-breaking spaces and special Unicode chars
    return re.sub(r"[\ufeff\u00a0\u200b]", "", value).strip()


class Command(BaseCommand):
    help = "Import constituencies and DUNs from Political Constituencies CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=str(DEFAULT_CSV),
            help=f"Path to CSV file (default: {DEFAULT_CSV})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without creating any records.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        dry_run = options["dry_run"]

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no records will be created.\n"))

        stats = {
            "constituencies_created": 0,
            "constituencies_updated": 0,
            "duns_created": 0,
            "duns_updated": 0,
            "rows_processed": 0,
            "errors": 0,
        }

        # Read CSV (note: header has typo "Parliment")
        # File uses cp1252 encoding (non-breaking spaces in party names)
        with open(file_path, "r", encoding="cp1252") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"Read {len(rows)} rows from {file_path.name}")

        # Track unique constituencies to avoid duplicate processing
        seen_constituencies = {}

        with transaction.atomic():
            for i, row in enumerate(rows, start=2):
                stats["rows_processed"] += 1

                # Parse DUN code/name
                dun_code, dun_name = parse_code_name(row.get("DUN", ""))
                if not dun_code:
                    self.stderr.write(f"  Row {i}: Cannot parse DUN '{row.get('DUN', '')}' — skipped")
                    stats["errors"] += 1
                    continue

                # Parse Parliament code/name (note CSV typo: "Parliment")
                parl_code, parl_name = parse_code_name(row.get("Parliment", ""))
                if not parl_code:
                    self.stderr.write(f"  Row {i}: Cannot parse Parliament '{row.get('Parliment', '')}' — skipped")
                    stats["errors"] += 1
                    continue

                # Determine state from DUN code prefix or constituency context
                # State is not a direct column — we'll derive it from the DUN data
                # For now, store empty and let import_schools fill it via MOE data
                state = ""

                # Create/update Constituency (once per unique code)
                if parl_code not in seen_constituencies:
                    constituency_data = {
                        "name": parl_name,
                        "state": state,
                        "mp_name": clean_party(row.get("Ahli Parliament", "")),
                        "mp_party": clean_party(row.get("MP Coalition (Party)", "")),
                        "mp_coalition": clean_party(row.get("MP Coalition", "")),
                    }

                    if not dry_run:
                        obj, created = Constituency.objects.update_or_create(
                            code=parl_code,
                            defaults=constituency_data,
                        )
                    else:
                        created = not Constituency.objects.filter(code=parl_code).exists()

                    if created:
                        stats["constituencies_created"] += 1
                    else:
                        stats["constituencies_updated"] += 1

                    seen_constituencies[parl_code] = True

                # Create/update DUN (keyed on code + constituency, since
                # DUN codes like N01 repeat across states)
                wkt = row.get("WKT", "").strip()
                dun_data = {
                    "name": dun_name,
                    "state": state,
                    "adun_name": clean_party(row.get("ADUN", "")),
                    "adun_party": clean_party(row.get("Coalition (Party)", "")),
                    "adun_coalition": clean_party(row.get("Coalition", "")),
                    "indian_population": parse_integer(row.get("Indians", "")),
                    "indian_percentage": parse_indian_percentage(row.get("Indians %", "")),
                    "boundary_wkt": wkt,
                }

                if not dry_run:
                    obj, created = DUN.objects.update_or_create(
                        code=dun_code,
                        constituency_id=parl_code,
                        defaults=dun_data,
                    )
                else:
                    created = not DUN.objects.filter(code=dun_code, constituency_id=parl_code).exists()

                if created:
                    stats["duns_created"] += 1
                else:
                    stats["duns_updated"] += 1

            # Now update constituency-level demographics by aggregating DUN data
            if not dry_run:
                self._update_constituency_demographics(rows)
                self._compute_constituency_boundaries()

            if dry_run:
                # Roll back the transaction
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"Rows processed:          {stats['rows_processed']}")
        self.stdout.write(f"Constituencies created:  {stats['constituencies_created']}")
        self.stdout.write(f"Constituencies updated:  {stats['constituencies_updated']}")
        self.stdout.write(f"DUNs created:            {stats['duns_created']}")
        self.stdout.write(f"DUNs updated:            {stats['duns_updated']}")
        self.stdout.write(f"Errors:                  {stats['errors']}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete — nothing was saved."))
        else:
            self.stdout.write(self.style.SUCCESS("\nImport complete."))

    def _update_constituency_demographics(self, rows):
        """Aggregate DUN-level demographics to constituency level."""
        constituency_data = {}

        for row in rows:
            parl_code, _ = parse_code_name(row.get("Parliment", ""))
            if not parl_code:
                continue

            if parl_code not in constituency_data:
                constituency_data[parl_code] = {
                    "indian_population": 0,
                    "total_population": 0,
                    "incomes": [],
                    "poverty_rates": [],
                    "ginis": [],
                    "unemployment_rates": [],
                }

            data = constituency_data[parl_code]
            indian_pop = parse_integer(row.get("Indians", ""))
            if indian_pop:
                data["indian_population"] += indian_pop

            income = parse_income(row.get("Ave. Income", ""))
            if income:
                data["incomes"].append(income)

            poverty = parse_decimal(row.get("Incidence of Poverty", ""))
            if poverty is not None:
                data["poverty_rates"].append(poverty)

            gini = parse_decimal(row.get("GINI", ""))
            if gini is not None:
                data["ginis"].append(gini)

            unemp = parse_decimal(row.get("Unemployment Rate", ""))
            if unemp is not None:
                data["unemployment_rates"].append(unemp)

        for code, data in constituency_data.items():
            update_fields = {
                "indian_population": data["indian_population"] or None,
            }
            if data["incomes"]:
                update_fields["avg_income"] = round(sum(data["incomes"]) / len(data["incomes"]))
            if data["poverty_rates"]:
                update_fields["poverty_rate"] = round(sum(data["poverty_rates"]) / len(data["poverty_rates"]), 2)
            if data["ginis"]:
                update_fields["gini"] = round(sum(data["ginis"]) / len(data["ginis"]), 3)
            if data["unemployment_rates"]:
                update_fields["unemployment_rate"] = round(sum(data["unemployment_rates"]) / len(data["unemployment_rates"]), 2)

            Constituency.objects.filter(code=code).update(**update_fields)

    def _compute_constituency_boundaries(self):
        """Compute constituency boundaries by unioning their DUN polygons."""
        from shapely import wkt as shapely_wkt
        from shapely.ops import unary_union

        updated = 0
        for constituency in Constituency.objects.prefetch_related("duns").all():
            dun_geometries = []
            for dun in constituency.duns.all():
                if dun.boundary_wkt:
                    try:
                        geom = shapely_wkt.loads(dun.boundary_wkt)
                        dun_geometries.append(geom)
                    except Exception:
                        logger.warning(
                            "Invalid WKT for DUN %s %s, skipping",
                            dun.code, dun.name,
                        )

            if dun_geometries:
                merged = unary_union(dun_geometries)
                constituency.boundary_wkt = merged.wkt
                constituency.save(update_fields=["boundary_wkt"])
                updated += 1

        self.stdout.write(f"Computed boundaries for {updated} constituencies.")
