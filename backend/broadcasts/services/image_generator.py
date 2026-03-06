"""Generate editorial-style hero images for intelligence emails via Gemini."""

import base64
import logging
import os

from google import genai

logger = logging.getLogger(__name__)

STYLE_PROMPTS = {
    "parliament": (
        "Create a New Yorker magazine style editorial illustration. "
        "The scene depicts a Malaysian parliament chamber with elements "
        "related to Tamil schools. Muted colour palette, elegant "
        "single-scene composition, slightly satirical tone. "
        "No text or words in the image. Landscape format, 640x300 pixels."
    ),
    "news": (
        "Create a New Yorker magazine style editorial cartoon illustration. "
        "The scene depicts a Malaysian Tamil school setting relevant to the "
        "news. Muted watercolour palette, elegant single-scene composition, "
        "storytelling quality. "
        "No text or words in the image. Landscape format, 640x300 pixels."
    ),
    "monthly": (
        "Create an editorial illustration in the style of a data "
        "visualisation artwork. Abstract representation of trends and "
        "patterns related to Malaysian Tamil schools. Purple and blue "
        "colour palette, geometric elements, analytical feel. "
        "No text or words in the image. Landscape format, 640x300 pixels."
    ),
}


def generate_hero_image(content_summary: str, style: str = "news") -> str | None:
    """Generate a hero image for an intelligence email.

    Args:
        content_summary: Brief description of the email content
            (used to contextualise the image).
        style: One of 'parliament', 'news', 'monthly'.

    Returns:
        Base64 data URI string (data:image/png;base64,...) or None on failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — cannot generate hero image")
        return None

    style_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["news"])
    full_prompt = (
        f"{style_prompt}\n\n"
        f"Context for this specific image: {content_summary}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=full_prompt,
            config=genai.types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        # Extract image from response
        for part in response.candidates[0].content.parts:
            if hasattr(part, "image") and part.image is not None:
                image_bytes = part.image.image_bytes
                b64 = base64.b64encode(image_bytes).decode("utf-8")
                return f"data:image/png;base64,{b64}"

        logger.warning("Gemini response contained no image")
        return None

    except Exception:
        logger.exception("Failed to generate hero image")
        return None
