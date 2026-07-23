"""Seed SchoolAlias records from existing School data.

Usage:
    python manage.py seed_aliases           # Create aliases for all schools
    python manage.py seed_aliases --clear   # Delete existing aliases first

For each school, generates:
- OFFICIAL: full MOE name (e.g. "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM")
- SHORT: short_name (e.g. "SJK(T) Ladang Bikam")
- COMMON: name without SJK(T) prefix (e.g. "Ladang Bikam")
- COMMON: SJKT variant without brackets (e.g. "SJKT Ladang Bikam")
- COMMON: without "Ladang" for estate schools (e.g. "SJK(T) Bikam")
- COMMON: full Malay form (e.g. "Sekolah Jenis Kebangsaan Tamil Ladang Bikam")
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

    # 6. "Without Ladang" variant — MPs commonly drop "Ladang" when referencing
    # estate schools (e.g. "SJK(T) Serendah" instead of "SJK(T) Ladang Serendah")
    if school.short_name and re.search(r"\bLadang\b", school.short_name, re.IGNORECASE):
        without_ladang = re.sub(
            r"\s*\bLadang\b\s*",
            " ",
            school.short_name,
            flags=re.IGNORECASE,
        ).strip()
        # Clean up double spaces
        without_ladang = re.sub(r"\s+", " ", without_ladang)
        if without_ladang and without_ladang.lower() != school.short_name.lower():
            add(without_ladang, SchoolAlias.AliasType.COMMON)

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

    # 7. Full Malay form without brackets — "Sekolah Jenis Kebangsaan Tamil <name>"
    # Hansard text often uses this form instead of the official "... (TAMIL) ..." form.
    if school.name:
        malay_variant = re.sub(
            r"^SEKOLAH JENIS KEBANGSAAN\s*\(TAMIL\)\s+",
            "Sekolah Jenis Kebangsaan Tamil ",
            school.name,
            flags=re.IGNORECASE,
        )
        if malay_variant and malay_variant.lower() != school.name.lower():
            add(malay_variant, SchoolAlias.AliasType.COMMON)

    # 8. Sprint 28 — Bhg ⇔ Bahagian ⇔ Division bridge. Articles and
    # journalists routinely write "Bahagian N" or "Division N" where the
    # MOE canonical short_name uses "Bhg N" (or vice versa). The
    # variant generator in the news matcher doesn't bridge these
    # spellings, so without alias coverage Strategy 5 falls back to a
    # single-token icontains match and lands on whichever school
    # happens to have the matching suffix word — causing the Sprint 27
    # NBD4079 (Ladang Labu Bhg 4) mis-tagging where 7 articles went to
    # ABDB006 ("Jendarata Bahagian Alpha", the only DB school with
    # "Bahagian") or MBD0067 ("Kemuning Kru Division").
    #
    # For any school whose short_name (or name-without-prefix) contains
    # `\b(Bhg|Bahagian|Division)\s*(\d+|IV|III|II)\b`, emit variants
    # for the other two spellings — same in every other respect.
    candidates = []
    if school.short_name:
        candidates.append(school.short_name)
    if stripped and stripped != (school.short_name or ""):
        candidates.append(stripped)

    # "Div" added 2026-07-23 — the abbreviation was missing, so The Star's
    # "SJK(T) Ladang Labu Div 4" resolved to nothing. The news matcher now
    # bridges these spellings at match time too (news_analyser
    # `_generate_name_variants`), so alias rows are no longer the only path.
    _BHG_RE = re.compile(
        r"\b(Bhg|Bahagian|Div|Division)\.?\s+"
        r"(\d+|IV|III|II|I|Empat|Lima|Tiga|Dua|Satu)\b",
        re.IGNORECASE,
    )
    _BHG_SYNONYMS = ["Bhg", "Bahagian", "Div", "Division"]
    for base in list(candidates):
        match = _BHG_RE.search(base)
        if not match:
            continue
        original_word = match.group(1)
        for synonym in _BHG_SYNONYMS:
            if synonym.lower() == original_word.lower():
                continue
            variant = (
                base[: match.start(1)]
                + synonym
                + base[match.end(1) :]
            )
            add(variant, SchoolAlias.AliasType.COMMON)

    # 9. Common Malay abbreviation ↔ full-form bridge. Journalists, news
    # cards, community writeups, and search-box users routinely swap
    # abbreviated ↔ spelled-out forms of common place-name particles. MOE's
    # canonical short_name uses one form; the wild spelling is often the
    # other. Without alias coverage, a user searching "Sungai Muar" won't
    # find "SJK(T) Ladang Sg Muar", and "Sri Alam" won't find "Seri Alam".
    #
    # For each variant pair, if the current base_text contains one form on
    # a word boundary, emit the swapped variant. Applied to short_name +
    # prefix-stripped short_name; the base MOE `name` field is ALL CAPS
    # and doesn't benefit from this transformation.
    _VARIANT_PAIRS = [
        ("Sri", "Seri"),      # Sanskrit ↔ Malay spelling of the honorific
        ("Bkt", "Bukit"),     # abbreviated ↔ full: hill
        ("Tmn", "Taman"),     # abbreviated ↔ full: garden / township
        ("Jln", "Jalan"),     # abbreviated ↔ full: road
        ("Kg", "Kampung"),    # abbreviated ↔ full: village
        ("Sg", "Sungai"),     # abbreviated ↔ full: river
        ("St", "Saint"),      # anglicised ↔ full: saint (mission schools)
        ("Ldg", "Ladang"),    # abbreviated ↔ full: estate / plantation
    ]
    for base in list(candidates):
        for canonical, full in _VARIANT_PAIRS:
            for a, b in [(canonical, full), (full, canonical)]:
                pattern = re.compile(rf"\b{re.escape(a)}\b", re.IGNORECASE)
                if pattern.search(base):
                    variant = pattern.sub(b, base)
                    add(variant, SchoolAlias.AliasType.COMMON)

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
