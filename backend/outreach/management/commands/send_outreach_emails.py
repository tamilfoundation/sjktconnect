"""Send outreach introduction emails to schools via Brevo.

Usage:
    python manage.py send_outreach_emails                       # All schools with email
    python manage.py send_outreach_emails --limit 10            # First 10 schools
    python manage.py send_outreach_emails --state Johor         # Only Johor schools
    python manage.py send_outreach_emails --dry-run             # Preview without sending
"""

from django.core.management.base import BaseCommand

from outreach.models import OutreachEmail
from outreach.services.email_sender import send_outreach_email
from schools.models import School


class Command(BaseCommand):
    help = "Send outreach introduction emails to schools."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max number of emails to send (0 = all).",
        )
        parser.add_argument(
            "--state",
            type=str,
            default="",
            help="Filter by state name (e.g. 'Johor').",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview which schools would receive emails without sending.",
        )

    def handle(self, *args, **options):
        # Only schools with an email address that haven't been emailed yet
        already_emailed = set(
            OutreachEmail.objects.filter(
                status__in=[OutreachEmail.Status.SENT, OutreachEmail.Status.PENDING],
            ).values_list("school_id", flat=True)
        )

        qs = School.objects.filter(is_active=True).exclude(email="")
        if options["state"]:
            qs = qs.filter(state__iexact=options["state"])

        schools = [s for s in qs if s.moe_code not in already_emailed]

        if options["limit"]:
            schools = schools[: options["limit"]]

        self.stdout.write(f"Schools to email: {len(schools)}")

        if options["dry_run"]:
            for school in schools:
                self.stdout.write(
                    f"  {school.moe_code} {school.short_name} → {school.email}"
                )
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
            return

        sent = 0
        failed = 0
        for i, school in enumerate(schools, 1):
            self.stdout.write(
                f"[{i}/{len(schools)}] {school.moe_code} → {school.email}..."
            )
            record = send_outreach_email(school, school.email)
            if record.status == OutreachEmail.Status.SENT:
                self.stdout.write(self.style.SUCCESS(f"  Sent."))
                sent += 1
            else:
                self.stdout.write(self.style.ERROR(
                    f"  Failed: {record.error_message}"
                ))
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(f"Done. Sent: {sent}, Failed: {failed}.")
        )
