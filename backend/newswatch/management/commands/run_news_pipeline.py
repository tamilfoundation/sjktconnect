"""Run the full news pipeline: fetch → extract → analyse."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the full news pipeline: fetch alerts, extract articles, analyse."

    def handle(self, *args, **options):
        self.stdout.write("Step 1/3: Fetching news alerts...")
        call_command("fetch_news_alerts")

        self.stdout.write("Step 2/3: Extracting articles...")
        call_command("extract_articles")

        self.stdout.write("Step 3/3: Analysing articles...")
        call_command("analyse_news_articles")

        self.stdout.write(self.style.SUCCESS("News pipeline complete."))
