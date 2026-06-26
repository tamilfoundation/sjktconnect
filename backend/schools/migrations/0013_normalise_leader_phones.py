"""Backfill SchoolLeader.phone with +60-X XXX XXXX format.

Owner-reported 2026-06-26: leader phones display inconsistently with
school phones — `0122090008` vs `+60-5 548 4299`. School phone goes
through `format_phone()` at import (Sprint 3.1); leader phones were
entered raw and never normalised. Sprint 28 added serializer-level
normalisation for future edits; this migration cleans up existing rows.

Skips sentinel no-value markers (TIADA / N/A / -). Idempotent:
re-running it leaves already-formatted values unchanged because
`format_phone` short-circuits when the input already starts with
`+60-`. Reversible (best-effort — original raw form isn't preserved,
so revert strips the formatting back to digits).

Note (Sprint 28.1, 2026-06-26): originally ran in prod with a broken
`format_phone()` (didn't recognise mobile prefixes 010-019). Sibling
migration `0014_normalise_leader_phones_with_mobile` re-runs after
the fix in `schools/utils.py`. On a fresh install today, 0013 does
all the work and 0014 is a no-op. Kept as a pair for prod history.
"""

from django.db import migrations


_SENTINELS = {"tiada", "n/a", "na", "none", "-"}


def normalise_phones(apps, schema_editor):
    SchoolLeader = apps.get_model("schools", "SchoolLeader")
    from schools.utils import format_phone

    updated = unchanged = skipped = 0
    for leader in SchoolLeader.objects.exclude(phone="").exclude(phone__isnull=True):
        raw = (leader.phone or "").strip()
        if not raw:
            continue
        if raw.lower() in _SENTINELS:
            skipped += 1
            continue
        formatted = format_phone(raw)
        if formatted and formatted != raw:
            leader.phone = formatted
            leader.save(update_fields=["phone"])
            updated += 1
        else:
            unchanged += 1
    print(
        f"  leader phones: +{updated} normalised, "
        f"{unchanged} already correct/unparseable, "
        f"{skipped} sentinel no-value"
    )


def revert_phones(apps, schema_editor):
    # Strip formatting back to digits-only — original raw form isn't
    # recoverable but digits-only is the lowest-common-denominator.
    SchoolLeader = apps.get_model("schools", "SchoolLeader")
    import re
    reverted = 0
    for leader in SchoolLeader.objects.filter(phone__startswith="+60-"):
        digits = re.sub(r"\D", "", leader.phone)
        # Drop +60 prefix → prepend 0
        if digits.startswith("60"):
            digits = "0" + digits[2:]
        leader.phone = digits
        leader.save(update_fields=["phone"])
        reverted += 1
    print(f"  leader phones: -{reverted} reverted to digits-only")


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0012_fix_no_space_after_period_names"),
    ]

    operations = [
        migrations.RunPython(normalise_phones, reverse_code=revert_phones),
    ]
