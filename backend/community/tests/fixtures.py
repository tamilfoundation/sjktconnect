"""Shared test helpers for the community app."""

import io
import random

from PIL import Image


def _noisy_image(width: int, height: int, seed: int = 0) -> Image.Image:
    """Image with random pixel noise, so two calls with different seeds
    produce visually different images (and therefore different pHashes).

    Solid-colour images all hash to the same pHash regardless of colour or
    size — perceptual hashing is by design tolerant of those changes. Tests
    that need distinct pHashes must use actual visual variation.
    """
    rng = random.Random(seed)
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    # Paint a coarse 16×16 grid of random colours; cheap and distinguishes
    # well at the 8×8 hash resolution used by imagehash.phash.
    block = max(1, min(width, height) // 16)
    for y in range(0, height, block):
        for x in range(0, width, block):
            colour = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
            for yy in range(y, min(y + block, height)):
                for xx in range(x, min(x + block, width)):
                    pixels[xx, yy] = colour
    return img


def valid_png_bytes(width: int = 800, height: int = 600, seed: int = 1) -> bytes:
    """Return PNG bytes for a noisy in-memory image (above 640×400)."""
    img = _noisy_image(width, height, seed)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def valid_jpeg_bytes(width: int = 800, height: int = 600, seed: int = 1) -> bytes:
    """Return JPEG bytes for a noisy in-memory image (above 640×400)."""
    img = _noisy_image(width, height, seed)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()
