"""Add aliases for schools the news matcher historically failed to resolve.

News articles routinely spell these schools differently from the MOE
canonical short_name:

    BBD5045  SJK(T) Kuala Kubu Bharu       articles say "Baru" (no h)
    ABD6102  SJK(T) St Teresa's Convent    articles say "St. Theresa Convent"
                                            (dot after St + extra h + no 's)
    BBD4063  SJK(T) Ldg West Country 'Timur'   articles say "West Country (Timur)"
                                                (parens + no Ldg)
    BBD9461  SJK(T) Ldg West Country 'Barat'   same pattern as Timur

Single-letter or punctuation differences are below the threshold for
fuzzy matching (false-positive risk too high) but are easy to handle
as curated aliases. The news matcher now consults SchoolAlias as
Strategy 1.5 (Sprint 24 #10h), so these rows take effect immediately.

Idempotent + reversible. Safe to re-run; safe on environments missing
one of these schools.
"""

from django.db import migrations


# Each entry: (moe_code, alias_text). Alias_normalized is computed below
# using the same shape as hansard.management.commands.seed_aliases.
_ALIASES = [
    # SJK(T) Kuala Kubu Bharu — article spells "Baru" (no h)
    ("BBD5045", "SJK(T) Kuala Kubu Baru"),
    ("BBD5045", "Kuala Kubu Baru"),

    # SJK(T) St Teresa's Convent — articles vary on dot, Theresa/Teresa, 's
    ("ABD6102", "SJK(T) St. Theresa Convent"),
    ("ABD6102", "SJK(T) St Theresa Convent"),
    ("ABD6102", "SJK(T) St. Teresa Convent"),
    ("ABD6102", "SJK(T) St Theresa's Convent"),
    ("ABD6102", "St. Theresa Convent"),
    ("ABD6102", "St Theresa Convent"),
    ("ABD6102", "St Theresa's Convent"),

    # SJK(T) Ldg West Country 'Timur' — article uses parens + drops Ldg
    ("BBD4063", "SJK(T) West Country (Timur)"),
    ("BBD4063", "SJK(T) Ladang West Country (Timur)"),
    ("BBD4063", "West Country (Timur)"),
    ("BBD4063", "SJK(T) Ldg West Country (Timur)"),

    # SJK(T) Ldg West Country 'Barat' — same pattern, pre-emptive
    ("BBD9461", "SJK(T) West Country (Barat)"),
    ("BBD9461", "SJK(T) Ladang West Country (Barat)"),
    ("BBD9461", "West Country (Barat)"),
    ("BBD9461", "SJK(T) Ldg West Country (Barat)"),
]


def _normalize(text: str) -> str:
    """Same shape as hansard.management.commands.seed_aliases.normalize_alias."""
    import re
    return re.sub(r"\s+", " ", text.lower().strip())


def add_news_match_aliases(apps, schema_editor):
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
        f"  news-match aliases: +{added} added, "
        f"{skipped_existing} already present, "
        f"{skipped_missing} skipped (school not in DB)"
    )


def remove_news_match_aliases(apps, schema_editor):
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
    print(f"  news-match aliases: -{removed} removed")


class Migration(migrations.Migration):

    dependencies = [
        ("hansard", "0008_add_jenderata_spelling_aliases"),
    ]

    operations = [
        migrations.RunPython(
            add_news_match_aliases,
            reverse_code=remove_news_match_aliases,
        ),
    ]
