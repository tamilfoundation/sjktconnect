"""
Service for sending subscriber-related emails via Brevo transactional API.

Handles confirmation/welcome emails when new subscribers join.
Falls back to console logging when BREVO_API_KEY is not set (dev mode).
"""

import logging
import os

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_confirmation_email(subscriber):
    """
    Send a welcome/confirmation email to a new subscriber.

    Includes links to manage preferences and unsubscribe.
    In dev mode (no BREVO_API_KEY), logs to console instead.

    Returns True if sent (or logged in dev), False on failure.
    """
    api_key = os.environ.get("BREVO_API_KEY")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    preferences_url = "%s/preferences/%s/" % (frontend_url, subscriber.unsubscribe_token)
    unsubscribe_url = "%s/unsubscribe/%s/" % (frontend_url, subscriber.unsubscribe_token)

    subject = "Welcome to SJK(T) Connect"
    html_content = _build_confirmation_html(
        subscriber.name or "there",
        preferences_url,
        unsubscribe_url,
    )

    if not api_key:
        logger.info(
            "DEV MODE — Confirmation email for %s: preferences %s, unsubscribe %s",
            subscriber.email,
            preferences_url,
            unsubscribe_url,
        )
        return True

    payload = {
        "sender": {
            "name": "SJK(T) Connect",
            "email": "noreply@tamilschool.org",
        },
        "to": [{"email": subscriber.email, "name": subscriber.name}],
        "subject": subject,
        "htmlContent": html_content,
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Confirmation email sent to %s", subscriber.email)
        return True

    except requests.RequestException as exc:
        logger.exception(
            "Failed to send confirmation email to %s: %s",
            subscriber.email,
            exc,
        )
        return False


def _build_confirmation_html(name, preferences_url, unsubscribe_url):
    """Build the HTML body for the welcome/confirmation email."""
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #ffffff; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
            <h2 style="color: #4f46e5;">Welcome to SJK(T) Connect</h2>
            <p>Dear %s,</p>
            <p>Thank you for subscribing to SJK(T) Connect &mdash; Malaysia&rsquo;s
            Tamil school intelligence and advocacy platform.</p>
            <p>You&rsquo;ll receive updates on:</p>
            <ul>
                <li><strong>Parliament Watch</strong> &mdash; How MPs speak about Tamil schools</li>
                <li><strong>News Watch</strong> &mdash; Tamil school news monitoring</li>
                <li><strong>Monthly Intelligence Blast</strong> &mdash; Data-driven school insights</li>
            </ul>
            <p style="text-align: center; margin: 30px 0;">
                <a href="%s"
                   style="background-color: #4f46e5; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Manage Your Preferences
                </a>
            </p>
            <p>You can customise which updates you receive or unsubscribe at any time.</p>
        </div>
        <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p>SJK(T) Connect &mdash; Tamil School Intelligence &amp; Advocacy Platform</p>
            <p>
                <a href="%s" style="color: #666; text-decoration: underline;">Manage Preferences</a>
                &nbsp;&middot;&nbsp;
                <a href="%s" style="color: #666; text-decoration: underline;">Unsubscribe</a>
            </p>
            <p>An initiative of the Malaysian Community Education Foundation (MCEF)</p>
        </div>
    </div>
</body>
</html>""" % (name, preferences_url, preferences_url, unsubscribe_url)
