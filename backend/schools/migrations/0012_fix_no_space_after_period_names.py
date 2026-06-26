"""Fix MOE-source names that have NO SPACE after a period.

Owner-reported 2026-06-26: SJK(T) Kg.Simee should be SJK(T) Kg. Simee
(space after the period). Audit of the April 2026 MOE Excel revealed
3 SJKT schools where MOE wrote `WORD.WORD` (no space after period):

    ABD2166  KG.SIMEE         → Kg. Simee
    JBD2049  CEP.NIYOR KLUANG → Cep. Niyor Kluang
    NBD6010  DATO' K.PATHMANABAN → Dato' K. Pathmanaban

This is a source-data quality issue, not a conversion bug — our
`to_proper_case` correctly title-cases what it receives. Future imports
of the same Excel will re-introduce these short_names, so we ALSO need
a periodic-import-time normalisation; that's a follow-up to
import_schools.py. This migration is the immediate visible fix.

Reversible. Idempotent: only updates rows whose short_name matches the
exact bad pattern (skips if the human/operator has already fixed it).
"""

from django.db import migrations


# Each entry: (moe_code, current bad short_name, target good short_name, current bad official name, target good official name).
_FIXES = [
    (
        "ABD2166",
        "SJK(T) Kg.Simee",
        "SJK(T) Kg. Simee",
        "Sekolah Jenis Kebangsaan (Tamil) Kg.Simee",
        "Sekolah Jenis Kebangsaan (Tamil) Kg. Simee",
    ),
    (
        "JBD2049",
        "SJK(T) Cep.Niyor Kluang",
        "SJK(T) Cep. Niyor Kluang",
        "Sekolah Jenis Kebangsaan (Tamil) Cep.Niyor Kluang",
        "Sekolah Jenis Kebangsaan (Tamil) Cep. Niyor Kluang",
    ),
    (
        "NBD6010",
        "SJK(T) Dato' K.Pathmanaban",
        "SJK(T) Dato' K. Pathmanaban",
        "Sekolah Jenis Kebangsaan (Tamil) Dato' K.Pathmanaban",
        "Sekolah Jenis Kebangsaan (Tamil) Dato' K. Pathmanaban",
    ),
]


def fix_names(apps, schema_editor):
    School = apps.get_model("schools", "School")
    fixed = skipped = missing = 0
    for moe, bad_short, good_short, bad_name, good_name in _FIXES:
        try:
            school = School.objects.get(moe_code=moe)
        except School.DoesNotExist:
            missing += 1
            continue
        changed = False
        if school.short_name == bad_short:
            school.short_name = good_short
            changed = True
        if school.name == bad_name:
            school.name = good_name
            changed = True
        if changed:
            school.save(update_fields=["short_name", "name", "updated_at"])
            fixed += 1
        else:
            skipped += 1
    print(
        f"  no-space-after-period name fixes: +{fixed} fixed, "
        f"{skipped} already correct, {missing} school(s) not in DB"
    )


def revert_names(apps, schema_editor):
    School = apps.get_model("schools", "School")
    reverted = 0
    for moe, bad_short, good_short, bad_name, good_name in _FIXES:
        try:
            school = School.objects.get(moe_code=moe)
        except School.DoesNotExist:
            continue
        changed = False
        if school.short_name == good_short:
            school.short_name = bad_short
            changed = True
        if school.name == good_name:
            school.name = bad_name
            changed = True
        if changed:
            school.save(update_fields=["short_name", "name", "updated_at"])
            reverted += 1
    print(f"  no-space-after-period name fixes: -{reverted} reverted")


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0011_normalise_state_names"),
    ]

    operations = [
        migrations.RunPython(fix_names, reverse_code=revert_names),
    ]
