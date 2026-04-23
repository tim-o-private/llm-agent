"""Unit tests for chatServer.lib.slugify — edge cases per SPEC-053 AC-03."""

from __future__ import annotations

import pytest

from chatServer.lib.slugify import slugify


class TestSlugify:
    """AC-03: deterministic name → slug conversion."""

    def test_simple_name(self):
        assert slugify("Sarah Chen") == "sarah-chen"

    def test_trailing_punctuation(self):
        assert slugify("Acme Corp.") == "acme-corp"

    def test_unicode_smart_quote(self):
        # Typographic right-single-quote (U+2019) has no ASCII mapping
        assert slugify("O’Brien & Associates") == "obrien-associates"

    def test_ascii_apostrophe(self):
        # ASCII apostrophe becomes a hyphen separator
        assert slugify("O'Brien") == "o-brien"

    def test_ampersand(self):
        assert slugify("Salt & Pepper") == "salt-pepper"

    def test_consecutive_spaces(self):
        assert slugify("Foo   Bar   Baz") == "foo-bar-baz"

    def test_already_slugified(self):
        assert slugify("sarah-chen") == "sarah-chen"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_numbers_preserved(self):
        assert slugify("Q3 Planning 2026") == "q3-planning-2026"

    def test_leading_trailing_special_chars(self):
        assert slugify("---Hello World---") == "hello-world"

    def test_unicode_accented(self):
        # NFKD decomposition strips the accent from e-acute
        assert slugify("Café") == "cafe"

    def test_all_special_chars(self):
        assert slugify("!!!") == ""

    def test_long_name_truncated(self):
        long_name = "a" * 300
        result = slugify(long_name)
        assert len(result) <= 200

    def test_mixed_case(self):
        assert slugify("CamelCaseCompany") == "camelcasecompany"

    def test_tabs_and_newlines(self):
        assert slugify("hello\tworld\nfoo") == "hello-world-foo"
