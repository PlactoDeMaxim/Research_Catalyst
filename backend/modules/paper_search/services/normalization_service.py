"""
Normalization Service

Cleans and standardizes paper metadata fields across different providers.
"""

import re
import unicodedata


def normalize_title(title: str) -> str:
    """Lowercase, strip whitespace, collapse spaces, remove punctuation."""
    t = title.lower().strip()
    t = re.sub(r"\s+", " ", t)
    # Remove accents
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return t


def normalize_author_name(name: str) -> str:
    """Lowercase, strip, remove diacritics."""
    n = name.lower().strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return n


def normalize_doi(doi: str | None) -> str | None:
    """Lowercase and strip DOI, remove URL prefix if present."""
    if not doi:
        return None
    d = doi.strip().lower()
    # Remove common URL prefixes
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"):
        if d.startswith(prefix):
            d = d[len(prefix):]
            break
    return d or None
