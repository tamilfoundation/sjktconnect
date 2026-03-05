"""Seed the 5 known parliamentary meetings and assign existing sittings."""

from django.db import migrations


MEETINGS = [
    {
        "name": "First Meeting of the Fourth Term 2025",
        "short_name": "1st Meeting 2025",
        "term": 4,
        "session": 1,
        "year": 2025,
        "start_date": "2025-02-04",
        "end_date": "2025-03-27",
    },
    {
        "name": "Special Meeting of the Fourth Term 2025",
        "short_name": "Special Meeting 2025",
        "term": 4,
        "session": 0,
        "year": 2025,
        "start_date": "2025-05-05",
        "end_date": "2025-05-05",
    },
    {
        "name": "Second Meeting of the Fourth Term 2025",
        "short_name": "2nd Meeting 2025",
        "term": 4,
        "session": 2,
        "year": 2025,
        "start_date": "2025-07-14",
        "end_date": "2025-08-21",
    },
    {
        "name": "Third Meeting of the Fourth Term 2025",
        "short_name": "3rd Meeting 2025",
        "term": 4,
        "session": 3,
        "year": 2025,
        "start_date": "2025-10-06",
        "end_date": "2025-12-04",
    },
    {
        "name": "First Meeting of the Fifth Term 2026",
        "short_name": "1st Meeting 2026",
        "term": 5,
        "session": 1,
        "year": 2026,
        "start_date": "2026-01-20",
        "end_date": "2026-04-03",
    },
]


def seed_meetings(apps, schema_editor):
    ParliamentaryMeeting = apps.get_model("parliament", "ParliamentaryMeeting")
    HansardSitting = apps.get_model("hansard", "HansardSitting")

    for data in MEETINGS:
        meeting = ParliamentaryMeeting.objects.create(**data)

        # Assign sittings whose date falls within this meeting's range
        HansardSitting.objects.filter(
            sitting_date__gte=data["start_date"],
            sitting_date__lte=data["end_date"],
            meeting__isnull=True,
        ).update(meeting=meeting)


def unseed_meetings(apps, schema_editor):
    ParliamentaryMeeting = apps.get_model("parliament", "ParliamentaryMeeting")
    HansardSitting = apps.get_model("hansard", "HansardSitting")
    HansardSitting.objects.filter(meeting__isnull=False).update(meeting=None)
    ParliamentaryMeeting.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("parliament", "0002_meeting_report"),
        ("hansard", "0004_meeting_report"),
    ]

    operations = [
        migrations.RunPython(seed_meetings, unseed_meetings),
    ]
