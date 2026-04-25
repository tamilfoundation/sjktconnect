"""Service for harvesting school images from Google APIs.

Sources:
- SATELLITE: Google Static Maps API (constructed from GPS coordinates)
- PLACES: Google Places API (real photos of the school)

Sprint 13: bytes are downloaded once and uploaded to Supabase Storage via
SchoolImage.image_file. The legacy image_url field is no longer populated
for new harvest runs (kept on the model for unmigrated rows).
"""

import logging
import os
import uuid

import requests
from django.core.files.base import ContentFile

from outreach.models import SchoolImage
from schools.models import School

logger = logging.getLogger(__name__)

STATIC_MAPS_BASE = "https://maps.googleapis.com/maps/api/staticmap"
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_PHOTO_BASE = "https://places.googleapis.com/v1"

# Don't try to download more than 5 MB per image (matches the Sprint 14 cap).
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _get_api_key() -> str:
    """Get Google Maps API key from environment."""
    return os.environ.get(
        "GOOGLE_MAPS_API_KEY",
        os.environ.get("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY", ""),
    )


def _download_bytes(url: str, *, timeout: int = 30) -> bytes | None:
    """Download a URL and return bytes, or None on failure / oversize."""
    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        # Don't load oversized payloads into memory
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                logger.warning("Image at %s exceeds %d bytes — skipping", url, MAX_IMAGE_BYTES)
                return None
            chunks.append(chunk)
        return b"".join(chunks)
    except requests.RequestException:
        logger.exception("Failed to download %s", url)
        return None


def harvest_satellite_image(school: School) -> SchoolImage | None:
    """Create a satellite static map image for a school using GPS coordinates.

    Bytes are downloaded from Google Static Maps and uploaded to Supabase
    Storage via SchoolImage.image_file. The remote URL contains an API key,
    so we never store it.

    Returns the created/updated SchoolImage or None on failure.
    """
    if not school.gps_lat or not school.gps_lng:
        logger.warning(
            "School %s has no GPS coordinates — skipping satellite",
            school.moe_code,
        )
        return None

    api_key = _get_api_key()
    if not api_key:
        logger.warning("No Google Maps API key — skipping satellite")
        return None

    fetch_url = (
        f"{STATIC_MAPS_BASE}"
        f"?center={school.gps_lat},{school.gps_lng}"
        f"&zoom=18&size=640x400&maptype=satellite"
        f"&key={api_key}"
    )

    image_bytes = _download_bytes(fetch_url)
    if image_bytes is None:
        return None

    # Determine if this should be primary (only if no existing primary)
    has_primary = school.images.filter(is_primary=True).exists()

    # Delete existing SATELLITE row before recreating (one slot, one source)
    school.images.filter(source=SchoolImage.Source.SATELLITE).delete()

    image = SchoolImage(
        school=school,
        source=SchoolImage.Source.SATELLITE,
        image_url="",  # legacy field — no longer populated
        is_primary=not has_primary,
        width=640,
        height=400,
        attribution="Google Maps",
    )
    filename = f"satellite-{uuid.uuid4().hex[:12]}.png"
    image.image_file.save(filename, ContentFile(image_bytes), save=True)
    return image


def harvest_places_images(
    school: School, max_photos: int = 3
) -> list[SchoolImage]:
    """Search Google Places for the school and fetch up to *max_photos* photos.

    Bytes are downloaded from Places photo URLs and uploaded to Supabase
    Storage. Performs a clean re-harvest: deletes any existing PLACES images
    for the school before creating new ones. The first photo becomes primary.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("No Google Maps API key — skipping Places search")
        return []

    search_query = school.short_name or school.name
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.photos",
    }
    body: dict = {
        "textQuery": search_query,
        "maxResultCount": 1,
    }
    if school.gps_lat and school.gps_lng:
        body["locationBias"] = {
            "circle": {
                "center": {
                    "latitude": float(school.gps_lat),
                    "longitude": float(school.gps_lng),
                },
                "radius": 5000.0,
            }
        }

    try:
        resp = requests.post(
            PLACES_SEARCH_URL, headers=headers, json=body, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        logger.exception("Places API search failed for %s", school.moe_code)
        return []

    places = data.get("places", [])
    if not places:
        logger.info("No Places result for %s", school.moe_code)
        return []

    place = places[0]
    photos = place.get("photos", [])
    if not photos:
        logger.info("No photos for %s in Places", school.moe_code)
        return []

    # Clean re-harvest: remove old Places images
    school.images.filter(source=SchoolImage.Source.PLACES).delete()

    # Demote existing primaries so the first Places photo can take over
    school.images.filter(is_primary=True).update(is_primary=False)

    created: list[SchoolImage] = []
    for i, photo in enumerate(photos[:max_photos]):
        photo_name = photo["name"]
        fetch_url = (
            f"{PLACES_PHOTO_BASE}/{photo_name}/media"
            f"?maxWidthPx=640&key={api_key}"
        )
        image_bytes = _download_bytes(fetch_url)
        if image_bytes is None:
            continue

        attribution = ""
        author_attrs = photo.get("authorAttributions", [])
        if author_attrs:
            attribution = author_attrs[0].get("displayName", "")

        image = SchoolImage(
            school=school,
            source=SchoolImage.Source.PLACES,
            image_url="",  # legacy field
            is_primary=(i == 0),
            width=photo.get("widthPx", 640),
            height=photo.get("heightPx"),
            attribution=attribution,
            photo_reference=photo_name,
        )
        filename = f"places-{uuid.uuid4().hex[:12]}.jpg"
        image.image_file.save(filename, ContentFile(image_bytes), save=True)
        created.append(image)

    return created


def harvest_places_image(school: School) -> SchoolImage | None:
    """Backwards-compatible wrapper — returns the first Places image or None."""
    images = harvest_places_images(school, max_photos=1)
    return images[0] if images else None


def harvest_images_for_school(
    school: School, sources: list[str] | None = None
) -> list[SchoolImage]:
    """Harvest all available images for a school.

    Args:
        school: The school to harvest images for.
        sources: List of sources to try. Default: ["satellite", "places"].

    Returns:
        List of created SchoolImage objects.
    """
    if sources is None:
        sources = ["satellite", "places"]

    results = []

    if "satellite" in sources:
        img = harvest_satellite_image(school)
        if img:
            results.append(img)

    if "places" in sources:
        imgs = harvest_places_images(school)
        results.extend(imgs)

    return results
