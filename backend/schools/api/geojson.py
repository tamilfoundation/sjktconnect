"""GeoJSON conversion helpers using shapely."""

import logging

from shapely import wkt as shapely_wkt
from shapely.geometry import mapping

logger = logging.getLogger(__name__)


def to_feature(wkt_string, properties):
    """Convert a WKT string + properties dict into a GeoJSON Feature.

    Returns None if the WKT is invalid.
    """
    try:
        geom = shapely_wkt.loads(wkt_string)
        return {
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": properties,
        }
    except Exception:
        logger.warning("Invalid WKT: %.50s...", wkt_string)
        return None


def to_feature_collection(features):
    """Wrap a list of GeoJSON Features into a FeatureCollection."""
    return {
        "type": "FeatureCollection",
        "features": features,
    }
