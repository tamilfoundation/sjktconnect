"""Service for harvesting school images from Google APIs.

Supports two sources:
- SATELLITE: Google Static Maps API (constructed from GPS coordinates)
- PLACES: Google Places API (real photos of the school)
"""

import logging
import os

import requests

from outreach.models import SchoolImage
from schools.models import School

logger = logging.getLogger(__name__)

STATIC_MAPS_BASE = "https://maps.googleapis.com/maps/api/staticmap"
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_PHOTO_BASE = "https://places.googleapis.com/v1"


def _get_api_key() -> str:
    """Get Google Maps API key from environment."""
    return os.environ.get(
        "GOOGLE_MAPS_API_KEY",
        os.environ.get("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY", ""),
    )


def harvest_satellite_image(school: School) -> SchoolImage | None:
    """Create a satellite static map image for a school using GPS coordinates.

    Returns the created/updated SchoolImage or None if the school has no GPS data.
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

    image_url = (
        f"{STATIC_MAPS_BASE}"
        f"?center={school.gps_lat},{school.gps_lng}"
        f"&zoom=18&size=640x400&maptype=satellite"
        f"&key={api_key}"
    )

    # Determine if this should be primary (only if no existing primary)
    has_primary = school.images.filter(is_primary=True).exists()

    image, _ = SchoolImage.objects.update_or_create(
        school=school,
        source=SchoolImage.Source.SATELLITE,
        defaults={
            "image_url": image_url,
            "is_primary": not has_primary,
            "width": 640,
            "height": 400,
            "attribution": "Google Maps",
        },
    )
    return image


def harvest_places_images(
    school: School, max_photos: int = 3
) -> list[SchoolImage]:
    """Search Google Places for the school and fetch up to *max_photos* photos.

    Performs a clean re-harvest: deletes any existing PLACES images for the
    school before creating new ones.  The first photo is set as primary
    (demoting any other primaries); subsequent photos are non-primary.

    Returns a list of created SchoolImage objects (may be empty).
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
        photo_url = (
            f"{PLACES_PHOTO_BASE}/{photo_name}/media"
            f"?maxWidthPx=640&key={api_key}"
        )

        attribution = ""
        author_attrs = photo.get("authorAttributions", [])
        if author_attrs:
            attribution = author_attrs[0].get("displayName", "")

        image = SchoolImage.objects.create(
            school=school,
            source=SchoolImage.Source.PLACES,
            image_url=photo_url,
            is_primary=(i == 0),
            width=photo.get("widthPx", 640),
            height=photo.get("heightPx"),
            attribution=attribution,
            photo_reference=photo_name,
        )
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
