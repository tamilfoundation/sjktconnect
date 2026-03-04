"""Fix YMHA abbreviation casing: 'Ymha' → 'YMHA'."""

from django.db import migrations


def fix_ymha_case(apps, schema_editor):
    School = apps.get_model("schools", "School")
    updated = School.objects.filter(moe_code="ABD6101").update(
        name="Sekolah Jenis Kebangsaan (Tamil) YMHA",
        short_name="SJK(T) YMHA",
    )
    if updated:
        print(f"  Fixed YMHA casing for {updated} school(s)")


def reverse(apps, schema_editor):
    School = apps.get_model("schools", "School")
    School.objects.filter(moe_code="ABD6101").update(
        name="Sekolah Jenis Kebangsaan (Tamil) Ymha",
        short_name="SJK(T) Ymha",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0004_add_school_leader"),
    ]

    operations = [
        migrations.RunPython(fix_ymha_case, reverse),
    ]
