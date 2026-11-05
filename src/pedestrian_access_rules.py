"""Pedestrian-access rules for the Shanghai OSM-derived network.

Rules follow the OSM default-access table for mainland China where defined.
Explicit foot/access tags override defaults. `motorroad=yes` is treated as
motorway-like and therefore non-pedestrian unless foot access is explicitly
allowed. `service` and `track` use the worldwide fallback when China-specific
defaults are not listed. This is a routing model, not field verification.
"""
from __future__ import annotations

EXPLICIT_FOOT_ALLOW = {"yes", "designated", "permissive", "official"}
EXPLICIT_FOOT_DENY = {"no", "private"}

CHINA_DEFAULT_FOOT_ALLOWED = {
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "unclassified", "residential", "living_street", "road",
    "pedestrian", "path", "cycleway", "footway",
}
WORLDWIDE_FALLBACK_FOOT_ALLOWED = {"service", "track"}
SEMANTIC_PEDESTRIAN_CLASSES = {"steps"}
DEFAULT_FOOT_DENIED = {"motorway", "motorway_link"}


def _norm(value) -> str:
    return str(value or "").strip().lower()


def classify_pedestrian_access(tags: dict) -> tuple[bool, str]:
    """Return (allowed, basis) for pedestrian routing on one OSM way."""
    highway = _norm(tags.get("highway"))
    foot = _norm(tags.get("foot"))
    access = _norm(tags.get("access"))
    motorroad = _norm(tags.get("motorroad"))

    if foot in EXPLICIT_FOOT_ALLOW:
        return True, "explicit_foot_allow"
    if foot in EXPLICIT_FOOT_DENY:
        return False, "explicit_foot_deny"
    if access in EXPLICIT_FOOT_DENY:
        return False, "explicit_access_deny"
    if motorroad == "yes":
        return False, "motorroad_implied_foot_no"
    if highway in DEFAULT_FOOT_DENIED:
        return False, "china_default_motorway_foot_no"
    if highway in CHINA_DEFAULT_FOOT_ALLOWED:
        return True, "china_default_foot_allowed"
    if highway in WORLDWIDE_FALLBACK_FOOT_ALLOWED:
        return True, "worldwide_fallback_foot_allowed"
    if highway in SEMANTIC_PEDESTRIAN_CLASSES:
        return True, "pedestrian_semantic_class"
    return False, "unsupported_or_unknown_highway"


def retained_by_conservative_sensitivity(tags: dict) -> bool:
    """Road-class sensitivity retained from the existing strict experiment.

    Explicit OSM pedestrian restrictions still take precedence.
    """
    allowed, _ = classify_pedestrian_access(tags)
    if not allowed:
        return False
    highway = _norm(tags.get("highway"))
    return highway in {
        "footway", "pedestrian", "path", "steps", "living_street",
        "residential", "service", "unclassified", "track",
    }
