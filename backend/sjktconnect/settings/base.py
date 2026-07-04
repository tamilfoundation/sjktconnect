"""
Base settings for SJK(T) Connect.
Shared across development and production environments.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-dev-key-change-in-production"
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "corsheaders",
    "rest_framework",
    # Local apps
    "core",
    "schools",
    "hansard",
    "parliament",
    "accounts",
    "community",
    "outreach",
    "subscribers",
    "broadcasts",
    "newswatch",
    "donations",
    "feedback",
]

MIDDLEWARE = [
    # IP + UA blocks run FIRST so blocked scrapers never touch routing,
    # DB, or serializers — cheapest possible way to stop egress drain.
    # (Sprint 17 added IP block; Sprint 21 added UA block for AwarioBot
    # & friends that ignore robots.txt.)
    "core.middleware.IPBlockMiddleware",
    "core.middleware.UserAgentBlockMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "sjktconnect.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sjktconnect.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Asia/Kuala_Lumpur"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# MEDIA_ROOT is only used by FileSystemStorage fallback (local dev / tests).
# Production uses Supabase Storage via STORAGES["default"] — see below.
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

# Structured JSON logging for Cloud Run
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# CORS — allow Next.js frontend origins
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# Public URL for the backend — used when building absolute URLs (e.g. image
# URLs on SchoolImage records that need to resolve from the frontend domain).
BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "http://localhost:8000",
)

# --- Supabase Storage (S3-compatible) for school images ---
# Configured in Sprint 13. Used by SchoolImage.image_file via django-storages.
# When SUPABASE_STORAGE_ACCESS_KEY is unset (e.g. in local dev / tests),
# Django falls back to the default FileSystemStorage so tests don't need
# network access.
SUPABASE_STORAGE_ENDPOINT = os.environ.get("SUPABASE_STORAGE_ENDPOINT", "")
SUPABASE_STORAGE_REGION = os.environ.get("SUPABASE_STORAGE_REGION", "ap-southeast-1")
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "school-images")
SUPABASE_STORAGE_ACCESS_KEY = os.environ.get("SUPABASE_STORAGE_ACCESS_KEY", "")
SUPABASE_STORAGE_SECRET_KEY = os.environ.get("SUPABASE_STORAGE_SECRET_KEY", "")
# Public URL prefix (without the S3 protocol) where bucket files are served.
# Supabase Storage exposes objects at https://<project>.storage.supabase.co/storage/v1/object/public/<bucket>/<path>
SUPABASE_STORAGE_PUBLIC_URL = os.environ.get(
    "SUPABASE_STORAGE_PUBLIC_URL",
    SUPABASE_STORAGE_ENDPOINT.replace("/s3", "/object/public") if SUPABASE_STORAGE_ENDPOINT else "",
)

if SUPABASE_STORAGE_ACCESS_KEY and SUPABASE_STORAGE_SECRET_KEY:
    _default_storage = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": SUPABASE_STORAGE_ACCESS_KEY,
            "secret_key": SUPABASE_STORAGE_SECRET_KEY,
            "bucket_name": SUPABASE_STORAGE_BUCKET,
            "region_name": SUPABASE_STORAGE_REGION,
            "endpoint_url": SUPABASE_STORAGE_ENDPOINT,
            # Public bucket — no signed URLs needed
            "querystring_auth": False,
            # Path-based addressing for S3-compat services
            "addressing_style": "path",
            # Don't ACL — Supabase ignores ACLs and bucket policy controls access
            "default_acl": None,
            "file_overwrite": False,
            # Cache assets aggressively (rotated by content hash if needed)
            "object_parameters": {
                "CacheControl": "public, max-age=86400",
            },
            # Public URL prefix for serving (overrides default S3 URL builder)
            "custom_domain": (
                SUPABASE_STORAGE_PUBLIC_URL.replace("https://", "").rstrip("/")
                + f"/{SUPABASE_STORAGE_BUCKET}"
            ) if SUPABASE_STORAGE_PUBLIC_URL else None,
            "url_protocol": "https:",
        },
    }
else:
    # Local dev / tests: use sqlite-friendly filesystem storage.
    _default_storage = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    }

STORAGES = {
    "default": _default_storage,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# REST Framework defaults
# SessionAuthentication is pinned explicitly — it enforces CSRF on state-changing
# requests, which the SameSite=None session cookie workaround (see production.py)
# depends on. Do NOT add TokenAuthentication here without a CSRF compensating
# control: cross-site POSTs would succeed because SameSite=None attaches the
# session cookie to any origin. See docs/tech-debt.md TD-04 + TD-08.
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Photo upload rate limits (Sprint 14). Scopes used by community views.
    "DEFAULT_THROTTLE_RATES": {
        "photo_upload_user": "5/day",
        "photo_upload_school": "20/day",
        # Audit 2026-07-01: rate-limit donation status polling by IP.
        # Toyyib return-URL loops back here; even a bugged FE poll
        # shouldn't spam the endpoint.
        "donation_status": "30/hour",
        # Sprint 34: bucket public list endpoints by IP. Scrapers
        # rotating UAs slip past the Sprint 21 UA blocklist; a rate
        # cap is the deterministic guard. Rates chosen to comfortably
        # cover a real visitor's session while stopping bulk scraping.
        "public_search": "60/hour",
        "public_list": "120/hour",
    },
}

# Models tracked by AuditLog middleware
AUDIT_LOG_MODELS = [
    "schools.School",
    "schools.Constituency",
    "schools.DUN",
    "hansard.HansardSitting",
    "hansard.HansardMention",
    "hansard.SchoolAlias",
    "hansard.MentionedSchool",
    "parliament.MPScorecard",
    "parliament.SittingBrief",
    "subscribers.Subscriber",
    "subscribers.SubscriptionPreference",
    "broadcasts.Broadcast",
    "broadcasts.BroadcastRecipient",
]

# Magic Link Authentication
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Urgent alerts always go to admin review — Sprint 25 flipped the
# default in 2026-06-26 and the auto-send code path was retired
# 2026-07-01 (audit follow-up). Kept as a note here so a future
# `git log -S URGENT_ALERT_REQUIRE_REVIEW` finds the retirement.

# Toyyib Pay
TOYYIBPAY_BASE_URL = os.environ.get("TOYYIBPAY_BASE_URL", "https://toyyibpay.com")
TOYYIBPAY_SECRET_KEY = os.environ.get("TOYYIBPAY_SECRET_KEY", "")
TOYYIBPAY_CATEGORY_CODE = os.environ.get("TOYYIBPAY_CATEGORY_CODE", "")

# Google OAuth (for community sign-in)
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
