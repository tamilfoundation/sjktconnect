"""Aliases for SJK(T) Ldg Katumba (KBD0053) and SJK(T) Lorong Java (NBD4070).

Owner-flagged 2026-06-26: news articles correctly identify these
schools by name but the matcher can't resolve them to a moe_code.

KBD0053 — MOE canonical: "SJK(T) Ldg Katumba" (Kedah).
  Articles spell with silent-h: "SJK(T) Ladang Kathumba". Common Tamil
  transliteration variance for the k+aspirated-t sound. Not bridgeable
  in the variant generator without false-positive risk.

NBD4070 — MOE canonical: "SJK(T) Lorong Java" (Negeri Sembilan).
  Article spells in English: "SJK(T) Jawa Lane" (Lorong = Lane, Java
  in MS = Jawa in some English/Tamil sources). Cross-language alias,
  also school-specific.

Strategy 1.5 (Sprint 24) makes these effective immediately for FUTURE
analysis. Post-deploy `rematch_schools` re-resolves the existing
unmatched mentions (since their moe_code is empty, the historical
fast-path covers them).

Idempotent + reversible.
"""

from django.db import migrations


_ALIASES = [
    # KBD0053 — silent-h variants
    ("KBD0053", "SJK(T) Ladang Kathumba"),
    ("KBD0053", "SJK(T) Kathumba"),
    ("KBD0053", "SJK(T) Ldg Kathumba"),
    ("KBD0053", "Ladang Kathumba"),
    ("KBD0053", "Kathumba"),
    ("KBD0053", "SJKT Ladang Kathumba"),
    # NBD4070 — English / cross-language variants
    ("NBD4070", "SJK(T) Jawa Lane"),
    ("NBD4070", "SJK(T) Java Lane"),
    ("NBD4070", "SJK(T) Lorong Jawa"),
    ("NBD4070", "Jawa Lane"),
    ("NBD4070", "Java Lane"),
    ("NBD4070", "Lorong Jawa"),
    ("NBD4070", "SJKT Jawa Lane"),
    ("NBD4070", "SJKT Lorong Java"),
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
        f"  Kathumba/Jawa Lane aliases: +{added} added, "
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
    print(f"  Kathumba/Jawa Lane aliases: -{removed} removed")


class Migration(migrations.Migration):

    dependencies = [
        ("hansard", "0010_ladang_labu_bahagian_aliases"),
    ]

    operations = [
        migrations.RunPython(add_aliases, reverse_code=remove_aliases),
    ]
