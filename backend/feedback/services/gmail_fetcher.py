"""
Gmail fetcher service for inbound email replies.

Connects to the SJK(T) Connect Gmail account via the Gmail API,
fetches new unread messages, and creates InboundEmail records.
Deduplicates by gmail_message_id.
"""

import base64
import logging
import os
import re

from feedback.models import InboundEmail

logger = logging.getLogger(__name__)


def _parse_email_address(raw):
    """
    Parse a 'From' header into (name, email).

    Handles formats:
    - "reader@example.com" → ("", "reader@example.com")
    - "A Reader <reader@example.com>" → ("A Reader", "reader@example.com")
    - '"A Reader" <reader@example.com>' → ("A Reader", "reader@example.com")
    """
    if not raw:
        return "", ""

    match = re.match(r'^"?([^"<]*?)"?\s*<([^>]+)>$', raw.strip())
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip()
        return name, email

    # Plain email address
    return "", raw.strip()


def _detect_broadcast_type(subject):
    """
    Detect which broadcast type an email is replying to, based on subject line.

    Returns one of: PARLIAMENT_WATCH, NEWS_WATCH, MONTHLY_BLAST, or "".
    """
    if not subject:
        return ""

    subject_lower = subject.lower()

    if "parliament watch" in subject_lower:
        return "PARLIAMENT_WATCH"
    if "monthly intelligence blast" in subject_lower or "monthly blast" in subject_lower:
        return "MONTHLY_BLAST"
    if "news watch" in subject_lower or "urgent" in subject_lower:
        return "NEWS_WATCH"

    return ""


def _get_gmail_service():
    """
    Build a Gmail API service using OAuth2 credentials from environment variables.

    Required env vars:
    - GMAIL_CLIENT_ID
    - GMAIL_CLIENT_SECRET
    - GMAIL_REFRESH_TOKEN
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=os.environ.get("GMAIL_ACCESS_TOKEN", ""),
        refresh_token=os.environ.get("GMAIL_REFRESH_TOKEN", ""),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GMAIL_CLIENT_ID", ""),
        client_secret=os.environ.get("GMAIL_CLIENT_SECRET", ""),
    )

    if creds.expired or not creds.valid:
        creds.refresh(Request())

    return build("gmail", "v1", credentials=creds)


def _extract_body(payload):
    """
    Extract plain text body from a Gmail message payload.

    Handles both single-part messages and multipart messages
    (recursively searches for text/plain parts).
    """
    if not payload:
        return ""

    # Single-part message
    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Multipart message — search parts for text/plain
    parts = payload.get("parts", [])
    for part in parts:
        part_mime = part.get("mimeType", "")
        if part_mime == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="replace"
                )
        # Nested multipart (e.g., multipart/alternative inside multipart/mixed)
        if part_mime.startswith("multipart/"):
            nested = _extract_body(part)
            if nested:
                return nested

    return ""


def _get_header(headers, name):
    """Get a header value by name from a list of Gmail headers."""
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def fetch_new_emails(max_results=20):
    """
    Fetch new unread emails from Gmail and create InboundEmail records.

    Args:
        max_results: Maximum number of messages to fetch per call.

    Returns:
        dict with:
            - fetched: count of new InboundEmail records created
            - skipped: count of already-fetched messages
            - errors: list of error messages
    """
    result = {"fetched": 0, "skipped": 0, "errors": []}

    try:
        service = _get_gmail_service()
    except Exception as e:
        logger.error("Failed to connect to Gmail API: %s", e)
        result["errors"].append(f"Gmail API connection failed: {e}")
        return result

    # List unread messages in inbox
    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=max_results)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to list Gmail messages: %s", e)
        result["errors"].append(f"Gmail list failed: {e}")
        return result

    messages = response.get("messages", [])
    if not messages:
        logger.info("No new unread messages found.")
        return result

    # Batch-check existing message IDs to avoid N+1
    message_ids = [msg["id"] for msg in messages]
    existing_ids = set(
        InboundEmail.objects.filter(gmail_message_id__in=message_ids).values_list(
            "gmail_message_id", flat=True
        )
    )

    for msg_summary in messages:
        msg_id = msg_summary["id"]

        if msg_id in existing_ids:
            result["skipped"] += 1
            continue

        # Fetch full message
        try:
            full_msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
        except Exception as e:
            logger.error("Failed to fetch message %s: %s", msg_id, e)
            result["errors"].append(f"Failed to fetch {msg_id}: {e}")
            continue

        headers = full_msg.get("payload", {}).get("headers", [])
        from_raw = _get_header(headers, "From")
        subject = _get_header(headers, "Subject")
        from_name, from_email = _parse_email_address(from_raw)
        body_text = _extract_body(full_msg.get("payload", {}))
        thread_id = full_msg.get("threadId", "")
        broadcast_type = _detect_broadcast_type(subject)

        try:
            InboundEmail.objects.create(
                gmail_message_id=msg_id,
                gmail_thread_id=thread_id,
                from_email=from_email,
                from_name=from_name,
                subject=subject,
                body_text=body_text,
                source_broadcast_type=broadcast_type,
            )
            result["fetched"] += 1
            logger.info("Created InboundEmail: %s from %s", msg_id, from_email)
        except Exception as e:
            logger.error("Failed to create InboundEmail %s: %s", msg_id, e)
            result["errors"].append(f"Failed to save {msg_id}: {e}")

    logger.info(
        "Gmail fetch complete: %d fetched, %d skipped, %d errors",
        result["fetched"],
        result["skipped"],
        len(result["errors"]),
    )
    return result
