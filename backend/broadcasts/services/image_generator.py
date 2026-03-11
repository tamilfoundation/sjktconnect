"""Generate editorial-style hero images via Gemini scene brief + Nano Banana Pro."""

import base64
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

SCENE_BRIEF_PROMPT = (
    "You are an art director for a magazine. Describe a single visual scene "
    "for an editorial illustration based on this content. The scene should "
    "feature Malaysian Tamil schools (SJK(T)) and be suitable for a {style} "
    "email header image. Keep it to 2-3 sentences. No text in the image.\n\n"
    "Content: {summary}"
)

ILLUSTRATION_PROMPT = (
    "Create a New Yorker magazine style editorial illustration. "
    "Muted watercolour palette, elegant single-scene composition, "
    "storytelling quality. No text or words in the image. "
    "Landscape format, 640x300 pixels.\n\n"
    "Scene: {scene}"
)


def generate_hero_image(content_summary: str, style: str = "news") -> bytes | None:
    """Generate a hero image using two-step Gemini scene brief + Nano Banana Pro.

    Args:
        content_summary: Brief description of the email content.
        style: One of 'parliament', 'news', 'monthly'.

    Returns:
        PNG image bytes or None on failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — cannot generate hero image")
        return None

    try:
        client = genai.Client(api_key=api_key)

        # Step 1: Gemini distils content into a visual scene description
        scene_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=SCENE_BRIEF_PROMPT.format(
                style=style,
                summary=content_summary[:2000],
            ),
        )
        scene = scene_response.text.strip()
        logger.info("Hero image scene brief: %s", scene[:200])

    except Exception:
        logger.exception("Scene brief generation failed, using fallback")
        scene = "A Malaysian Tamil school building marked SJK(T) with community gathering"

    # Step 2: Nano Banana Pro draws the scene
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=ILLUSTRATION_PROMPT.format(scene=scene),
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                img_bytes = part.inline_data.data
                if isinstance(img_bytes, str):
                    img_bytes = base64.b64decode(img_bytes)
                return img_bytes

        logger.warning("Nano Banana Pro response contained no image")
        return None

    except Exception:
        logger.exception("Hero image generation failed")
        return None
