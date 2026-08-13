"""Tests für scripts/lib/ad.py — LDAP-Filter-Escaping (RFC 4515)."""

from __future__ import annotations

from scripts.lib import ad


def test_escape_filter_escapes_special_chars():
    assert ad.escape_filter("a*b(c)\\d") == "a\\2ab\\28c\\29\\5cd"


def test_escape_filter_leaves_plain_value():
    assert ad.escape_filter("App-XYZ-Users") == "App-XYZ-Users"


def test_escape_filter_wildcard_keeps_star():
    # '*' bleibt Wildcard, aber Klammern/Backslash werden escaped.
    assert ad.escape_filter_wildcard("App-*-(x)") == "App-*-\\28x\\29"


def test_recursive_member_rule_oid():
    assert ad.RECURSIVE_MEMBER_RULE == "1.2.840.113556.1.4.1941"
