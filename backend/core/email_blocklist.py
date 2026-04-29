"""
Shared email-domain blocklist.

Bots regularly submit contact / subscribe forms with obviously fake
addresses (test@example.com, reader@example.com, ...). Brevo blocks
the outbound delivery, but each attempt still costs us API calls,
DB rows, and log noise. Reject these at the API boundary instead.

Sprint 22 hotfix (2026-04-29). Single source of truth used by:
  * subscribers/api/serializers.py SubscribeSerializer
  * schools/api/views.py ContactFormView
  * feedback/services/responder.py auto_respond
"""

import re

# Domains that are reserved for documentation / testing per RFC 2606
# plus the most common disposable-email providers seen in support
# threads. Add (don't speculate) — only block what we've actually
# observed or what RFC says is unroutable.
BLOCKED_DOMAINS = frozenset({
    # RFC 2606 reserved
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "test.test",
    "test",
    # Common disposable / throwaway
    "mailinator.com",
    "guerrillamail.com",
    "tempmail.com",
    "tempmail.io",
    "10minutemail.com",
    "yopmail.com",
    "throwaway.email",
    "dispostable.com",
    "trashmail.com",
    "sharklasers.com",
    "maildrop.cc",
    "fakeinbox.com",
    "getnada.com",
})


# Suffix patterns — match the tail of the domain, not the whole thing.
# RFC 2606 reserves .test, .example, .invalid, .localhost as TLDs.
_BLOCKED_SUFFIXES = (
    ".test",
    ".example",
    ".invalid",
    ".localhost",
    ".local",
)


# Standard email shape: local@domain. We're not validating syntax here
# (that's the EmailField's job) — just extracting the domain to match.
_EMAIL_RE = re.compile(r"^[^@]+@(.+)$")


def is_blocked_email(email: str) -> bool:
    """Return True if the email's domain is on the blocklist.

    Match is case-insensitive. Bare strings or malformed emails return
    False (let the EmailField surface the validation error instead of
    silently treating "not an email" as "blocked email").
    """
    if not email:
        return False
    m = _EMAIL_RE.match(email.strip())
    if not m:
        return False
    domain = m.group(1).lower()
    if domain in BLOCKED_DOMAINS:
        return True
    if any(domain.endswith(suf) for suf in _BLOCKED_SUFFIXES):
        return True
    return False
