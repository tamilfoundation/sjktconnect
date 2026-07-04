"""
Production settings for SJK(T) Connect.
Deployed on Google Cloud Run with Supabase PostgreSQL.
"""

import os

import dj_database_url

from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is required in production")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# Cloud Run SSL termination (load balancer handles HTTPS)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Cloud Run handles this
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Default SameSite=Lax is correct now that frontend (tamilschool.org) and backend
# (api.tamilschool.org) are same-site (both subdomains of tamilschool.org), proxied
# through Cloudflare with end-to-end TLS. No SameSite=None workaround required.
SECURE_CONTENT_TYPE_NOSNIFF = True

# Database — Supabase PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    raise ValueError("DATABASE_URL is required in production")

# Brevo webhook HMAC secret — hard-required in prod (audit 2026-07-01).
# Without it, forged webhook events can flip BroadcastRecipient engagement
# fields and trigger auto-deactivate-after-N-hard-bounces on arbitrary subscribers.
BREVO_WEBHOOK_SECRET = os.environ.get("BREVO_WEBHOOK_SECRET")
if not BREVO_WEBHOOK_SECRET:
    raise ValueError("BREVO_WEBHOOK_SECRET is required in production")

# News Watch — Google Alerts RSS feed URLs (comma-separated env var)
_rss_feeds = os.environ.get("NEWS_WATCH_RSS_FEEDS", "")
NEWS_WATCH_RSS_FEEDS = [
    url.strip() for url in _rss_feeds.split(",") if url.strip()
]

# WhiteNoise for static files on Cloud Run.
# Inject the WhiteNoise static-files backend into the STORAGES dict that base.py
# already populates (with Supabase Storage as default for media files). Don't
# replace the dict entirely — that would lose the Supabase media config.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
