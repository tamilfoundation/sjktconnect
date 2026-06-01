"""Normalise state names across School, Constituency, DUN.

Two fixes in one pass:

1. Collapse "Wilayah Persekutuan <name>" (any case) to "W.P. <name>" so
   compact display surfaces (digest emails, sidebars, filter chips, SEO
   titles) don't wrap awkwardly. Storage becomes the single source of
   truth for state display — no per-component formatting needed.

2. Title-case the historical Constituency.state rows that were imported
   pre-normalisation in ALL CAPS ("JOHOR" -> "Johor" etc.). School.state
   was already title-cased by Sprint 3.1's data pass; Constituency was
   missed because the import gate (`if not constituency.state`) only
   fires on blank rows, so re-imports never corrected the casing.

Reversible: backward operation re-uppercases Constituency rows and
expands W.P. back to full Malay across all 3 tables.
"""

from django.db import migrations


# Forward mapping: any non-canonical state -> canonical form.
# Lower-case keys; we lookup case-insensitively. Values are the target
# display form (title-case for the 13 regular states; "W.P. <name>" for
# the 3 federal territories).
_CANONICAL = {
    "johor": "Johor",
    "kedah": "Kedah",
    "kelantan": "Kelantan",
    "melaka": "Melaka",
    "negeri sembilan": "Negeri Sembilan",
    "pahang": "Pahang",
    "perak": "Perak",
    "perlis": "Perlis",
    "pulau pinang": "Pulau Pinang",
    "sabah": "Sabah",
    "sarawak": "Sarawak",
    "selangor": "Selangor",
    "terengganu": "Terengganu",
    "wilayah persekutuan kuala lumpur": "W.P. Kuala Lumpur",
    "wilayah persekutuan putrajaya": "W.P. Putrajaya",
    "wilayah persekutuan labuan": "W.P. Labuan",
}


def normalise_states_forward(apps, schema_editor):
    """Rewrite every state field to its canonical form. Idempotent."""
    for model_label in ("School", "Constituency", "DUN"):
        Model = apps.get_model("schools", model_label)
        for row in Model.objects.exclude(state="").only("pk", "state"):
            target = _CANONICAL.get(row.state.strip().lower())
            if target and target != row.state:
                row.state = target
                row.save(update_fields=["state"])


def normalise_states_backward(apps, schema_editor):
    """Restore the prior representation as best we can.

    - W.P. variants expand back to full Malay.
    - Constituency rows that were UPPERCASE before this migration
      go back to UPPERCASE. We can't tell from the current state
      which model+row was originally uppercase, so we apply the
      heuristic that matches the pre-migration pattern: School +
      DUN stay title-case, Constituency goes UPPERCASE.
    """
    reverse_wp = {
        "W.P. Kuala Lumpur": "Wilayah Persekutuan Kuala Lumpur",
        "W.P. Putrajaya": "Wilayah Persekutuan Putrajaya",
        "W.P. Labuan": "Wilayah Persekutuan Labuan",
    }
    School = apps.get_model("schools", "School")
    Constituency = apps.get_model("schools", "Constituency")
    DUN = apps.get_model("schools", "DUN")

    for Model in (School, DUN):
        for row in Model.objects.exclude(state="").only("pk", "state"):
            if row.state in reverse_wp:
                row.state = reverse_wp[row.state]
                row.save(update_fields=["state"])

    for row in Constituency.objects.exclude(state="").only("pk", "state"):
        target = reverse_wp.get(row.state, row.state).upper()
        if target != row.state:
            row.state = target
            row.save(update_fields=["state"])


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0010_drop_last_verified_and_verified_by"),
    ]

    operations = [
        migrations.RunPython(
            normalise_states_forward,
            reverse_code=normalise_states_backward,
        ),
    ]
