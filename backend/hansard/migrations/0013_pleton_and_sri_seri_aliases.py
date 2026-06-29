"""Add aliases for two news-matcher misses surfaced 2026-06-29.

BERNAMA article 985 (Madani Adoption Tamil-school funding, 26 Jun 2026)
named four Johor SJK(T) schools; only two resolved to MOE codes.

    JBD1007  SJK(T) Ldg Sg Plentong       article: "Ladang Sungai Pleton"
                                            (Gemini transliteration dropped
                                            letters from Tamil பிளென்டாங்).
    JBD1029  SJK(T) Bandar Seri Alam      article: "Bandar Sri Alam"
                                            (Sri/Seri romanisation drift).

The Sri/Seri case is *also* covered by an `_ABBREV_MAP` swap added in the
same change — the alias here is belt-and-braces in case the variant
generator misses an edge form, and self-documents the JBD1029 mapping
for future maintainers.

The Plentong/Pleton case is a Gemini transliteration error, not an
abbreviation — the only durable fix is a curated alias.

Idempotent + reversible. Safe to re-run; safe on environments missing
one of these schools.
"""

from django.db import migrations


_ALIASES = [
    # JBD1007 — Plentong/Pleton transliteration drift
    ("JBD1007", "SJK(T) Ladang Sungai Pleton"),
    ("JBD1007", "Ladang Sungai Pleton"),
    ("JBD1007", "SJK(T) Ldg Sungai Pleton"),
    ("JBD1007", "SJK(T) Ladang Sg Pleton"),

    # JBD1029 — Sri/Seri romanisation drift (belt-and-braces with
    # _ABBREV_MAP["Sri"] = "Seri")
    ("JBD1029", "SJK(T) Bandar Sri Alam"),
    ("JBD1029", "Bandar Sri Alam"),
]


def _normalize(text: str) -> str:
    """Same shape as hansard.management.commands.seed_aliases.normalize_alias."""
    import re
    return re.sub(r"\s+", " ", text.lower().strip())


def add_aliases(apps, schema_editor):
    SchoolAlias = apps.get_model("hansard", "SchoolAlias")
    School = apps.get_model("schools", "School")

    added = skipped_missing = skipped_existing = 0
    for moe_code, alias_text in _ALIASES:
        try:
            school = School.objects.get(moe_code=moe_code)
        except School.DoesNotExist:
            skipped_missing += 1
            continue
        normalized = _normalize(alias_text)
        _, created = SchoolAlias.objects.get_or_create(
            school=school,
            alias_normalized=normalized,
            defaults={
                "alias": alias_text,
                "alias_type": "HANSARD",
            },
        )
        if created:
            added += 1
        else:
            skipped_existing += 1
    print(
        f"  pleton/sri-seri aliases: +{added} added, "
        f"{skipped_existing} already present, "
        f"{skipped_missing} skipped (school not in DB)"
    )


def remove_aliases(apps, schema_editor):
    SchoolAlias = apps.get_model("hansard", "SchoolAlias")
    School = apps.get_model("schools", "School")

    removed = 0
    for moe_code, alias_text in _ALIASES:
        try:
            school = School.objects.get(moe_code=moe_code)
        except School.DoesNotExist:
            continue
        deleted, _ = SchoolAlias.objects.filter(
            school=school,
            alias_normalized=_normalize(alias_text),
            alias_type="HANSARD",
        ).delete()
        removed += deleted
    print(f"  pleton/sri-seri aliases: -{removed} removed")


class Migration(migrations.Migration):

    dependencies = [
        ("hansard", "0012_alter_hansardsitting_status"),
    ]

    operations = [
        migrations.RunPython(add_aliases, reverse_code=remove_aliases),
    ]
