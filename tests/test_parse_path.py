"""
Tests for the path parser.

The path parser is the bridge between human-friendly key notation and
tomlrt's tuple-of-segments API. These tests ensure each supported syntax
variant produces the correct segment tuple, and that the parser doesn't
silently mangle bare keys under randomised input.
"""

from typing import Literal

from hypothesis import given
from hypothesis import strategies as st
from tryke import describe, expect, test

from tomlrt_cli.cli import _parse_path

# Unicode general categories for Hypothesis character strategies.
_UNICODE_CATEGORIES: tuple[Literal["L"], Literal["N"], Literal["P"]] = ("L", "N", "P")

with describe("bare dotted paths"):

    @test("simple dotted path")
    def test_simple_dotted():
        # The most common case — plain identifiers separated by dots.
        expect(_parse_path("version.v26.alpine")).to_equal(("version", "v26", "alpine"))

    @test("single segment")
    def test_single_segment():
        # Edge case: a path with no dots should still produce a
        # one-element tuple, not an empty result.
        expect(_parse_path("name")).to_equal(("name",))

    @test("empty string produces empty tuple")
    def test_empty_string():
        # Defensive: empty input should not crash.
        expect(_parse_path("")).to_equal(())

    @test("leading dot is treated as separator")
    def test_leading_dot():
        # Leading dot means "start with separator" — first segment
        # is whatever follows.
        expect(_parse_path(".a.b")).to_equal(("a", "b"))

    @test("trailing dot is ignored")
    def test_trailing_dot():
        # Trailing dot has nothing after it — no empty segment produced.
        expect(_parse_path("a.b.")).to_equal(("a", "b"))

    @test("adjacent dots produce no empty segments")
    def test_adjacent_dots():
        # Multiple consecutive dots are just multiple separators.
        expect(_parse_path("a..b")).to_equal(("a", "b"))


with describe("double-quoted keys"):

    @test("quoted key containing a dot")
    def test_quoted_dot():
        # Keys like "3.14" contain a dot that must not be treated as a
        # separator. Quoting protects the literal value.
        expect(_parse_path('version."3.14".alpine')).to_equal(("version", "3.14", "alpine"))

    @test("quoted key at start of path")
    def test_quoted_start():
        expect(_parse_path('"weird.key".child')).to_equal(("weird.key", "child"))

    @test("quoted key at end of path")
    def test_quoted_end():
        expect(_parse_path('parent."weird.key"')).to_equal(("parent", "weird.key"))


with describe("single-quoted keys"):

    @test("single-quoted key containing a dot")
    def test_single_quoted_dot():
        # Single quotes should work identically to double quotes.
        expect(_parse_path("version.'3.14'.alpine")).to_equal(("version", "3.14", "alpine"))

    @test("single-quoted key at start")
    def test_single_quoted_start():
        expect(_parse_path("'a.b'.c")).to_equal(("a.b", "c"))


with describe("bracket notation"):

    @test("bracket with double quotes")
    def test_bracket_double():
        # Bracket syntax mirrors JavaScript/jq conventions.
        expect(_parse_path('version["3.14"].alpine')).to_equal(("version", "3.14", "alpine"))

    @test("bracket with single quotes")
    def test_bracket_single():
        expect(_parse_path("version['3.14'].alpine")).to_equal(("version", "3.14", "alpine"))

    @test("unquoted bracket content")
    def test_bracket_unquoted():
        # Unquoted bracket: everything between [ and ] is the key.
        expect(_parse_path("version[alpine].pin")).to_equal(("version", "alpine", "pin"))

    @test("bracket at start of path")
    def test_bracket_start():
        expect(_parse_path('["top"].child')).to_equal(("top", "child"))


with describe("mixed notation"):

    @test("all styles combined in one path")
    def test_mixed():
        # Verifies the parser handles transitions between styles.
        expect(_parse_path('a["b"].c."d.e"')).to_equal(("a", "b", "c", "d.e"))

    @test("bracket immediately after bracket")
    def test_consecutive_brackets():
        expect(_parse_path('["a"]["b"]')).to_equal(("a", "b"))

    @test("dot between brackets")
    def test_dot_between_brackets():
        expect(_parse_path('["a"].["b"]')).to_equal(("a", "b"))


with describe("property-based tests"):

    @test("bare keys round-trip through parse")
    @given(
        st.lists(
            st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]*", fullmatch=True),
            min_size=1,
            max_size=5,
        )
    )
    def test_bare_keys_roundtrip(keys: list[str]):
        # Property: joining bare keys with dots and re-parsing must
        # yield the original list. This catches off-by-one errors and
        # ensures the parser doesn't consume characters it shouldn't.
        path = ".".join(keys)
        expect(_parse_path(path)).to_equal(tuple(keys))

    @test("quoted keys with dots round-trip through parse")
    @given(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=_UNICODE_CATEGORIES, blacklist_characters="\"'[]"),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=4,
        )
    )
    def test_quoted_keys_roundtrip(keys: list[str]):
        # Property: wrapping each key in double quotes and joining with
        # dots must produce the original keys after parsing. This covers
        # keys containing dots, spaces, and other special characters.
        path = ".".join(f'"{k}"' for k in keys)
        expect(_parse_path(path)).to_equal(tuple(keys))
