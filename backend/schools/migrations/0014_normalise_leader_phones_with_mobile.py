"""Re-run the leader-phone normalisation after the format_phone mobile fix.

Sprint 28 follow-up: migration 0013 normalised leader phones via
`format_phone()`, but at that time format_phone treated mobile prefixes
(01X) as unparseable — `_DOUBLE_DIGIT_AREA_CODES` only listed East-MY
landline codes (82-89). Result: 0013 normalised 0 mobile phones and
the owner-flagged "0122090008" stayed raw.

This migration re-runs the same backfill against the now-fixed
format_phone (which knows 010-019 mobile prefixes). Idempotent and
reversible.
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
        f"  leader phones (mobile-aware): +{updated} normalised, "
        f"{unchanged} already correct, {skipped} sentinel"
    )


def revert_phones(apps, schema_editor):
    # No-op: this migration only normalises rows that 0013 already
    # touched (or that 0013 missed due to the mobile-prefix bug). The
    # 0013 reverse handles the strip-to-digits path.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0013_normalise_leader_phones"),
    ]

    operations = [
        migrations.RunPython(normalise_phones, reverse_code=revert_phones),
    ]
