"""Enable pg_trgm extension for trigram similarity matching.

Only applies on PostgreSQL. SQLite (local dev) skips this safely.
The matcher module uses a Python fallback (difflib.SequenceMatcher)
when pg_trgm is not available.
"""

from django.db import migrations


def enable_pg_trgm(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")


def disable_pg_trgm(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP EXTENSION IF EXISTS pg_trgm;")


class Migration(migrations.Migration):

    dependencies = [
        ("hansard", "0002_add_school_alias_and_mentioned_school"),
    ]

    operations = [
        migrations.RunPython(enable_pg_trgm, disable_pg_trgm),
    ]
