"""Add aliases for SJK(T) Ladang Labu Bhg 4 (NBD4079) covering the
Bahagian/Division/Bhg variants that journalists actually write.

Sprint 27 #2 — investigation revealed 9 articles about NBD4079 in the
news DB, but only 2 were resolved correctly. The other 7 went to
ABDB006 (`SJK(T) Ladang Jendarata Bahagian Alpha Bernam`, the ONLY
other school with "Bahagian" in its short_name) or MBD0067
(`SJK(T) Ldg Kemuning Kru Division`, the ONLY other school with
"Division" in its short_name). The matcher's variant generator
doesn't bridge `Bhg ⇔ Bahagian ⇔ Division`, and when an article
mentions "SJKT Ladang Labu Bahagian 4" the matcher's exact-match
strategies land on whichever school has the matching suffix word.

This migration adds the specific NBD4079 aliases. A broader fix to
the variant generator (Bhg↔Bahagian↔Division everywhere) is a
follow-up — the targeted alias is the safer immediate fix.

After deploy, run `rematch_schools` against the 9 affected articles
to re-resolve them to NBD4079.

Idempotent + reversible.
"""

from django.db import migrations


_ALIASES = [
    ("NBD4079", "SJK(T) Ladang Labu Bahagian 4"),
    ("NBD4079", "SJK(T) Ladang Labu Bahagian IV"),
    ("NBD4079", "SJK(T) Ladang Labu Bahagian Empat"),
    ("NBD4079", "SJK(T) Ladang Labu Division 4"),
    ("NBD4079", "SJK(T) Ladang Labu Division IV"),
    ("NBD4079", "SJKT Ladang Labu Bahagian 4"),
    ("NBD4079", "SJKT Ladang Labu Division 4"),
    ("NBD4079", "Ladang Labu Bahagian 4"),
    ("NBD4079", "Ladang Labu Division 4"),
    ("NBD4079", "Ladang Labu Bhg 4"),
    ("NBD4079", "SJK(T) Ldg Labu Bahagian 4"),
    ("NBD4079", "SJK(T) Ldg Labu Bhg 4"),
    ("NBD4079", "SJK(T) Labu Bhg 4"),
]


def _normalize(text: str) -> str:
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
        _, created = SchoolAlias.objects.get_or_create(
            school=school,
            alias_normalized=_normalize(alias_text),
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
        f"  Ladang Labu Bahagian aliases: +{added} added, "
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
    print(f"  Ladang Labu Bahagian aliases: -{removed} removed")


class Migration(migrations.Migration):

    dependencies = [
        ("hansard", "0009_news_match_aliases"),
    ]

    operations = [
        migrations.RunPython(add_aliases, reverse_code=remove_aliases),
    ]
