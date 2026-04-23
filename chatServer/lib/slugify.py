"""Deterministic name-to-slug converter for entity doc filenames.

``slugify("Sarah Chen")`` → ``"sarah-chen"``
``slugify("Acme Corp.")`` → ``"acme-corp"``
``slugify("O'Brien & Associates")`` → ``"obrien-associates"``

Unicode is NFKD-normalised and stripped to ASCII before kebab-casing.
The result is safe as a filename and doubles as a wikilink target.
"""

from __future__ import annotations

import re
import unicodedata

# Safety cap: filesystem limit is typically 255 bytes; leave margin.
_MAX_SLUG_LEN = 200


def slugify(name: str) -> str:
    """Convert a display name to a kebab-case filename slug."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s[:_MAX_SLUG_LEN]
