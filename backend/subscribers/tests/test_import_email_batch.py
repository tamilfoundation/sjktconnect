"""Tests for the generic import_email_batch command."""

import csv

import pytest
from django.core.management import call_command

from subscribers.models import Subscriber, SubscriptionPreference


def _write_csv(path, rows, header=("email", "name")):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    return str(path)


@pytest.mark.django_db
def test_import_creates_subscribers_with_all_preferences(tmp_path):
    csv_path = _write_csv(tmp_path / "batch.csv", [
        ("alice@example.com", "Alice"),
        ("bob@example.com", "Bob"),
    ])
    call_command("import_email_batch", file=csv_path, source_tag="TF_TEST")

    assert Subscriber.objects.filter(source_tag="TF_TEST").count() == 2
    alice = Subscriber.objects.get(email="alice@example.com")
    assert alice.name == "Alice"
    assert alice.source == "BULK_IMPORT"
    assert alice.is_active
    # The whole point: enrolled in all newsletters at import time (no orphans)
    prefs = alice.preferences.all()
    assert prefs.count() == 3
    assert all(p.is_enabled for p in prefs)


@pytest.mark.django_db
def test_import_never_resurrects_unsubscribed(tmp_path):
    Subscriber.objects.create(email="gone@example.com", name="Gone", is_active=False)
    csv_path = _write_csv(tmp_path / "batch.csv", [("gone@example.com", "Gone Again")])

    call_command("import_email_batch", file=csv_path, source_tag="TF_TEST")

    s = Subscriber.objects.get(email="gone@example.com")
    assert s.is_active is False   # opting out stays opted out
    assert s.source_tag == ""     # not re-tagged into the batch


@pytest.mark.django_db
def test_import_is_idempotent_and_dedups_within_file(tmp_path):
    csv_path = _write_csv(tmp_path / "batch.csv", [
        ("dup@example.com", "Dup"),
        ("DUP@example.com", "Dup2"),  # same address, different case
    ])
    call_command("import_email_batch", file=csv_path, source_tag="TF_TEST")
    call_command("import_email_batch", file=csv_path, source_tag="TF_TEST")  # re-run

    assert Subscriber.objects.filter(email="dup@example.com").count() == 1
    assert SubscriptionPreference.objects.filter(
        subscriber__email="dup@example.com"
    ).count() == 3


@pytest.mark.django_db
def test_import_dry_run_writes_nothing(tmp_path):
    csv_path = _write_csv(tmp_path / "batch.csv", [("x@example.com", "X")])
    call_command("import_email_batch", file=csv_path, source_tag="TF_TEST", dry_run=True)
    assert not Subscriber.objects.filter(email="x@example.com").exists()


@pytest.mark.django_db
def test_import_skips_invalid_emails(tmp_path):
    csv_path = _write_csv(tmp_path / "batch.csv", [
        ("valid@example.com", "V"),
        ("not-an-email", "Bad"),
        ("", "Blank"),
    ])
    call_command("import_email_batch", file=csv_path, source_tag="TF_TEST")
    assert Subscriber.objects.filter(source_tag="TF_TEST").count() == 1


@pytest.mark.django_db
def test_import_enrols_existing_active_subscriber_missing_prefs(tmp_path):
    # An active subscriber with NO preference rows (the pre-fix orphan state)
    existing = Subscriber.objects.create(email="active@example.com", is_active=True)
    assert existing.preferences.count() == 0
    csv_path = _write_csv(tmp_path / "batch.csv", [("active@example.com", "Active")])

    call_command("import_email_batch", file=csv_path, source_tag="TF_TEST")

    assert existing.preferences.count() == 3  # back-filled
