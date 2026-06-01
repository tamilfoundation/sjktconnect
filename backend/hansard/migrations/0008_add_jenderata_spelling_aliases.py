"""Add 'Jenderata' spelling aliases for the 4 'Jendarata' schools.

News articles and other sources frequently spell the estate name with
an 'e' (Jenderata) while MOE records use 'a' (Jendarata). The matcher
needs explicit aliases to bridge the gap — fuzzy matching across all
528 schools risks false positives on other 1-letter typos.

The 4 affected schools:
    ABDB002  SJK(T) Ladang Jendarata 1
    ABDB003  SJK(T) Ladang Jendarata Bhg 2
    ABDB004  SJK(T) Ladang Jendarata Bhg 3
    ABDB006  SJK(T) Ladang Jendarata Bahagian Alpha Bernam

Idempotent: skips any (school, alias_normalized) row that already
exists. Safe to re-run; safe across re-imports.
"""

from django.db import migrations


# Each entry: (moe_code, alias_text). We add multiple alias variants per
# school so both "SJK(T) Ladang Jenderata 1" (with the SJK(T) prefix) and
# "Ladang Jenderata 1" (bare estate name) match. The matcher normalises
# to lowercase + collapsed whitespace before lookup, so casing here is
# preserved for the human-readable `alias` field only.
_ALIASES = [
    ("ABDB002", "SJK(T) Ladang Jenderata 1"),
    ("ABDB002", "Ladang Jenderata 1"),
    ("ABDB002", "Jenderata 1"),
    ("ABDB003", "SJK(T) Ladang Jenderata Bhg 2"),
    ("ABDB003", "SJK(T) Ladang Jenderata Bahagian 2"),
    ("ABDB003", "Ladang Jenderata Bhg 2"),
    ("ABDB003", "Jenderata 2"),
    ("ABDB004", "SJK(T) Ladang Jenderata Bhg 3"),
    ("ABDB004", "SJK(T) Ladang Jenderata Bahagian 3"),
    ("ABDB004", "Ladang Jenderata Bhg 3"),
    ("ABDB004", "Jenderata 3"),
    ("ABDB006", "SJK(T) Ladang Jenderata Bahagian Alpha Bernam"),
    ("ABDB006", "Ladang Jenderata Bahagian Alpha Bernam"),
    ("ABDB006", "Jenderata Alpha Bernam"),
]


def _normalize(text: str) -> str:
    """Same shape as hansard.management.commands.seed_aliases.normalize_alias."""
    import re
    return re.sub(r"\s+", " ", text.lower().strip())


def add_jenderata_aliases(apps, schema_editor):
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
        f"  jenderata aliases: +{added} added, "
        f"{skipped_existing} already present, "
        f"{skipped_missing} skipped (school not in DB)"
    )


def remove_jenderata_aliases(apps, schema_editor):
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
    print(f"  jenderata aliases: -{removed} removed")


class Migration(migrations.Migration):

    dependencies = [
        ("hansard", "0007_add_pipeline_version"),
        ("schools", "0011_normalise_state_names"),
    ]

    operations = [
        migrations.RunPython(
            add_jenderata_aliases,
            reverse_code=remove_jenderata_aliases,
        ),
    ]
