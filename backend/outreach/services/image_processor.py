"""Server-side validation + processing for community photo uploads.

Pillow validates format, size, and dimensions; strips EXIF; resizes to a
sane maximum; and computes a perceptual hash for dedup.

Sprint 14 — replaces the Sprint 8.2 base64-into-BinaryField flow.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import imagehash
from PIL import Image, ImageOps, UnidentifiedImageError

# Constraints per Image Library plan (docs/plans/2026-04-22-image-library-sprint-plan.md)
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_WIDTH = 640
MIN_HEIGHT = 400
MAX_DIMENSION = 1600  # longest edge after resize
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class UploadValidationError(ValueError):
    """Surfaced to the API layer as a 4xx with a stable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ProcessedImage:
    bytes: bytes
    content_type: str  # e.g. "image/jpeg"
    extension: str     # e.g. "jpg"
    width: int
    height: int
    phash: str         # 16-char hex perceptual hash


def _format_to_content_type(fmt: str) -> tuple[str, str]:
    """Map Pillow format → (content_type, file extension)."""
    if fmt == "JPEG":
        return "image/jpeg", "jpg"
    if fmt == "PNG":
        return "image/png", "png"
    if fmt == "WEBP":
        return "image/webp", "webp"
    raise UploadValidationError("unsupported_format", f"Unsupported format: {fmt}")


def process_upload(raw: bytes) -> ProcessedImage:
    """Validate + normalise an uploaded image. Raises UploadValidationError.

    Pipeline:
      1. Reject if >5 MB.
      2. Open with Pillow; reject if not JPEG/PNG/WebP.
      3. Reject if smaller than 640×400.
      4. Apply EXIF orientation, then strip EXIF.
      5. Resize so longest edge ≤1600px (preserve aspect).
      6. Re-encode (drops metadata) and compute perceptual hash.
    """
    if not raw:
        raise UploadValidationError("empty", "Empty upload.")
    if len(raw) > MAX_BYTES:
        raise UploadValidationError(
            "too_large",
            f"Image is {len(raw) // 1024} KB; max {MAX_BYTES // 1024} KB.",
        )

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()  # force decode so truncated files raise here, not later
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadValidationError("invalid_image", "File is not a valid image.") from exc

    fmt = (img.format or "").upper()
    if fmt not in ALLOWED_FORMATS:
        raise UploadValidationError(
            "unsupported_format",
            f"Format {fmt or 'unknown'} not allowed. Use JPEG, PNG, or WebP.",
        )

    # Apply EXIF orientation BEFORE measuring dimensions — a portrait phone
    # photo with EXIF orientation 6 is stored as landscape and would fail the
    # min-height check otherwise.
    img = ImageOps.exif_transpose(img)

    if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
        raise UploadValidationError(
            "too_small",
            f"Image is {img.width}×{img.height}; minimum {MIN_WIDTH}×{MIN_HEIGHT}.",
        )

    # Resize so the longest edge is at most MAX_DIMENSION.
    longest = max(img.width, img.height)
    if longest > MAX_DIMENSION:
        scale = MAX_DIMENSION / longest
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Convert palette/alpha to RGB for JPEG; keep PNG/WebP as RGBA-capable.
    if fmt == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")

    content_type, extension = _format_to_content_type(fmt)

    out = io.BytesIO()
    save_kwargs: dict = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs.update(quality=85, optimize=True, progressive=True)
    elif fmt == "PNG":
        save_kwargs.update(optimize=True)
    elif fmt == "WEBP":
        save_kwargs.update(quality=85, method=4)
    img.save(out, **save_kwargs)
    processed_bytes = out.getvalue()

    phash = str(imagehash.phash(img))

    return ProcessedImage(
        bytes=processed_bytes,
        content_type=content_type,
        extension=extension,
        width=img.width,
        height=img.height,
        phash=phash,
    )
