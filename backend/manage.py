#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from pathlib import Path


# Commands that write to the database. Running these against a production
# Supabase DB by accident (because .env auto-loads a prod DSN) has bitten us
# before — see docs/tech-debt.md TD-03. These require an explicit opt-in via
# SJKTCONNECT_ALLOW_PROD_DB=1 in the environment.
_DESTRUCTIVE_COMMANDS = {
    "migrate", "makemigrations", "flush", "loaddata", "sqlflush",
    "sqlmigrate", "sqlsequencereset", "reset_db", "createsuperuser",
    "changepassword", "import_schools", "import_constituencies",
    "import_subscribers", "import_bank_details", "import_ge15_results",
    "import_mp_profiles", "harvest_school_images", "seed_aliases",
    "rebuild_all_hansards", "run_hansard_pipeline", "analyse_mentions",
    "update_scorecards", "compose_news_digest", "send_welcome_email",
    "normalize_school_abbreviations",
}


def _check_prod_db():
    """Abort destructive commands against a prod DB unless explicitly allowed.

    A DATABASE_URL that isn't localhost/sqlite is treated as potentially
    production. Read-only commands (shell, test, check, etc.) always proceed —
    only destructive commands are gated.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return
    is_local = (
        "localhost" in db_url
        or "127.0.0.1" in db_url
        or db_url.startswith("sqlite")
    )
    if is_local:
        return

    # Print a warning banner on every invocation so the target is obvious.
    host = db_url.split("@")[-1].split("/")[0] if "@" in db_url else db_url
    sys.stderr.write(
        f"\n[manage.py] DATABASE_URL points to: {host}\n"
        f"[manage.py] Treating as PRODUCTION. "
        f"Set SJKTCONNECT_ALLOW_PROD_DB=1 to allow destructive commands.\n\n"
    )

    if os.environ.get("SJKTCONNECT_ALLOW_PROD_DB") == "1":
        return

    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command in _DESTRUCTIVE_COMMANDS:
        sys.stderr.write(
            f"[manage.py] REFUSING to run '{command}' against production DB.\n"
            f"[manage.py] If you are sure, export SJKTCONNECT_ALLOW_PROD_DB=1 first.\n"
        )
        sys.exit(1)


def main():
    """Run administrative tasks."""
    # Load .env from project root (one level up from backend/)
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv

        load_dotenv(env_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sjktconnect.settings.development")

    _check_prod_db()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
