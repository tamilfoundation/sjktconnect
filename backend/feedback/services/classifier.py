"""
AI classifier for inbound emails using Gemini.

Takes an InboundEmail, sends it to Gemini for classification,
and updates the model with the result.

Uses the google.genai SDK (same pattern as broadcasts/services/parliament_digest.py).
"""

import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

VALID_CLASSIFICATIONS = {
    "CORRECTION",
    "TIP",
    "COMPLAINT",
    "PRAISE",
    "QUESTION",
    "UNSUBSCRIBE",
    "IRRELEVANT",
}

CLASSIFIER_PROMPT = """\
You are classifying an email received in reply to an SJK(T) Connect broadcast \
(Tamil school intelligence platform in Malaysia).

Classify the email into exactly ONE of these categories:
- CORRECTION: The sender is correcting factual information (school names, dates, figures).
- TIP: The sender is sharing new information, leads, or insider knowledge.
- COMPLAINT: The sender is unhappy about the content, platform, or a school issue.
- PRAISE: The sender is expressing appreciation or positive feedback.
- QUESTION: The sender is asking a question that needs answering.
- UNSUBSCRIBE: The sender wants to stop receiving emails.
- IRRELEVANT: Auto-replies, spam, out-of-office, or unrelated content.

Also decide whether this email needs human escalation. Escalate if:
- The question is complex or policy-related
- The complaint is serious or involves a safety concern
- The tip involves sensitive or time-critical information
- You are unsure of the classification

Return ONLY valid JSON with these keys:
- "classification": one of the categories above (string)
- "reasoning": brief explanation of why (string)
- "escalate": whether a human should review this (boolean)

--- EMAIL ---
From: {from_name} <{from_email}>
Subject: {subject}
Body:
{body_text}
--- END EMAIL ---
"""


def classify_email(email):
    """
    Classify an InboundEmail using Gemini AI.

    Updates the email's classification, classification_reasoning,
    escalated, and response_status fields.

    Args:
        email: InboundEmail instance to classify.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping classification")
        return

    prompt = CLASSIFIER_PROMPT.format(
        from_name=email.from_name,
        from_email=email.from_email,
        subject=email.subject,
        body_text=email.body_text[:2000],  # Token budget: cap at 2000 chars
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        raw_text = response.text.strip()
    except Exception:
        logger.exception("Gemini API call failed for email %s", email.gmail_message_id)
        return

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON for email %s: %s",
            email.gmail_message_id,
            raw_text[:200],
        )
        email.classification = "UNCLASSIFIED"
        email.classification_reasoning = f"JSON parse error: {raw_text[:200]}"
        email.save(update_fields=["classification", "classification_reasoning"])
        return

    classification = data.get("classification", "UNCLASSIFIED")
    reasoning = data.get("reasoning", "")
    escalate = data.get("escalate", False)

    # Validate classification against allowed choices
    if classification not in VALID_CLASSIFICATIONS:
        logger.warning(
            "Invalid classification '%s' for email %s — defaulting to UNCLASSIFIED",
            classification,
            email.gmail_message_id,
        )
        classification = "UNCLASSIFIED"

    email.classification = classification
    email.classification_reasoning = reasoning

    if escalate:
        email.escalated = True
        email.response_status = "ESCALATED"

    email.save(
        update_fields=[
            "classification",
            "classification_reasoning",
            "escalated",
            "response_status",
        ]
    )

    logger.info(
        "Classified email %s as %s (escalate=%s)",
        email.gmail_message_id,
        classification,
        escalate,
    )
