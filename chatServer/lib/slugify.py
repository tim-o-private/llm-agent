"""Pure slugify function — converts display names to kebab-case filename slugs.

Shared by ThreadService (SPEC-054) and EntityService (SPEC-053).
"""

import re
import unicodedata


def slugify(name: str) -> str:
    """Convert a display name to a kebab-case filename slug.

    >>> slugify("Sarah Chen")
    'sarah-chen'
    >>> slugify("Acme Corp.")
    'acme-corp'
    >>> slugify("O'Brien & Associates")
    'obrien-associates'
    """
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")
