"""Seed SchoolAlias records from existing School data.

Usage:
    python manage.py seed_aliases           # Create aliases for all schools
    python manage.py seed_aliases --clear   # Delete existing aliases first

For each school, generates:
- OFFICIAL: full MOE name (e.g. "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM")
- SHORT: short_name (e.g. "SJK(T) Ladang Bikam")
- COMMON: name without SJK(T) prefix (e.g. "Ladang Bikam")
- COMMON: SJKT variant without brackets (e.g. "SJKT Ladang Bikam")
"""

import re

from django.core.management.base import BaseCommand

from hansard.models import SchoolAlias
from schools.models import School


def normalize_alias(text: str) -> str:
    """Normalise an alias for matching: lowercase, collapse whitespace, strip."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def generate_aliases_for_school(school: School) -> list[dict]:
    """Generate alias dicts for a single school.

    Returns a list of dicts with keys: alias, alias_normalized, alias_type.
    """
    aliases = []
    seen_normalized = set()

    def add(alias_text: str, alias_type: str):
        normalized = normalize_alias(alias_text)
        if not normalized or normalized in seen_normalized:
            return
        seen_normalized.add(normalized)
        aliases.append({
            "alias": alias_text,
            "alias_normalized": normalized,
            "alias_type": alias_type,
        })

    # 1. Official full name
    if school.name:
        add(school.name, SchoolAlias.AliasType.OFFICIAL)

    # 2. Short name
    if school.short_name:
        add(school.short_name, SchoolAlias.AliasType.SHORT)

    # 3. Name without SJK(T)/SJKT prefix — the distinctive part
    # Match patterns like "SJK(T) Ladang Bikam" → "Ladang Bikam"
    short = school.short_name or school.name
    stripped = re.sub(
        r"^(?:sjk\s*\(t\)|sjkt|s\.j\.k\.?\s*\(t\))\s+",
        "",
        short,
        flags=re.IGNORECASE,
    )
    if stripped and stripped.lower() != short.lower():
        add(stripped, SchoolAlias.AliasType.COMMON)

    # 4. SJKT variant (no brackets) — "SJKT Ladang Bikam"
    if school.short_name and "SJK(T)" in school.short_name.upper():
        sjkt_variant = re.sub(
            r"SJK\s*\(T\)",
            "SJKT",
            school.short_name,
            flags=re.IGNORECASE,
        )
        add(sjkt_variant, SchoolAlias.AliasType.COMMON)

    # 5. Full official name without "SEKOLAH JENIS KEBANGSAAN (TAMIL)" prefix
    if school.name:
        official_stripped = re.sub(
            r"^SEKOLAH JENIS KEBANGSAAN\s*\(TAMIL\)\s+",
            "",
            school.name,
            flags=re.IGNORECASE,
        )
        if official_stripped and official_stripped.lower() != school.name.lower():
            add(official_stripped, SchoolAlias.AliasType.COMMON)

    return aliases


class Command(BaseCommand):
    help = "Seed SchoolAlias records from School data (official, short, common variants)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing auto-generated aliases before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            # Only delete auto-generated types, preserve HANSARD type
            deleted, _ = SchoolAlias.objects.exclude(
                alias_type=SchoolAlias.AliasType.HANSARD
            ).delete()
            self.stdout.write(f"Deleted {deleted} existing aliases (preserved HANSARD type).")

        schools = School.objects.filter(is_active=True)
        total_schools = schools.count()
        self.stdout.write(f"Generating aliases for {total_schools} schools...")

        created_count = 0
        skipped_count = 0

        for school in schools:
            alias_dicts = generate_aliases_for_school(school)
            for ad in alias_dicts:
                _, created = SchoolAlias.objects.get_or_create(
                    school=school,
                    alias_normalized=ad["alias_normalized"],
                    defaults={
                        "alias": ad["alias"],
                        "alias_type": ad["alias_type"],
                    },
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done! {created_count} aliases created, {skipped_count} already existed."
        ))
        self.stdout.write(f"Total aliases in DB: {SchoolAlias.objects.count()}")
