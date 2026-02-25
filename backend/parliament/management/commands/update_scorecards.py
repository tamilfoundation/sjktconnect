"""Management command to recalculate all MP scorecards.

Usage:
    python manage.py update_scorecards
"""

import logging

from django.core.management.base import BaseCommand

from parliament.services.scorecard import update_all_scorecards

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recalculate all MP scorecards from analysed Hansard mentions."

    def handle(self, **options):
        self.stdout.write("Recalculating MP scorecards...")
        result = update_all_scorecards()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {result['created']} created, "
                f"{result['updated']} updated, "
                f"{result['deleted']} deleted."
            )
        )
