"""
CLI entry point for tomlrt-cli.

This module is the sole user-facing interface. It wires argument parsing to
tomlrt operations so that shell scripts and CI pipelines can read or
manipulate TOML files without writing Python.
"""

import argparse
import re
import sys
from importlib.metadata import version

import tomlrt

# ------------------------------------------------------------------------------
# PRIVATE FUNCTIONS


def _parse_path(path: str) -> tuple[str, ...]:
    """
    Convert a user-supplied key path string into a tuple of literal key
    segments that tomlrt can traverse.

    tomlrt's `install()` accepts either a dot-separated string (which it
    naively splits on `.`) or a tuple of literal segments. Naive splitting
    breaks when a key itself contains a dot (e.g., version "3.14"). This
    parser exists to let users express such keys with quoting or bracket
    notation while still producing the tuple that tomlrt needs.
    """
    segments: list[str] = []
    i = 0

    while i < len(path):
        # Dots are separators, not content — skip them.
        if path[i] == ".":
            i += 1

        elif path[i] == "[":
            # Bracket notation (version["3.14"]) lets users reference keys
            # that would be ambiguous in dotted form because the key value
            # itself contains dots or special characters.
            i += 1

            if i < len(path) and path[i] in ('"', "'"):
                quote = path[i]
                i += 1

                end = path.index(quote, i)
                segments.append(path[i:end])
                i = end + 1

                if i < len(path) and path[i] == "]":
                    i += 1

            else:
                # Unquoted bracket content — treat everything up to `]`
                # as the literal key name.
                end = path.index("]", i)
                segments.append(path[i:end])
                i = end + 1

        elif path[i] in ('"', "'"):
            # Inline quoted key (version."3.14".alpine) — the quotes
            # protect the enclosed value from being split on dots.
            quote = path[i]
            i += 1

            end = path.index(quote, i)
            segments.append(path[i:end])
            i = end + 1

        else:
            # Bare key — consume everything until the next delimiter.
            match = re.match(r'[^.\["\'\]]+', path[i:])

            if match:
                segments.append(match.group())
                i += match.end()

    return tuple(segments)


# ------------------------------------------------------------------------------
# PUBLIC FUNCTIONS


def main() -> int:
    """
    Parse CLI arguments and perform the requested TOML read operation.

    Designed to behave like jq for TOML: read a file, optionally drill into a
    specific path, and emit the result to stdout or a file.
    """
    parser = argparse.ArgumentParser(prog="tomlrt-cli", description="tomlrt-cli")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {version('tomlrt-cli')}")
    parser.add_argument("-o", "--output", help="output file path (default: stdout)")
    parser.add_argument("-p", "--path", help="TOML key path")
    parser.add_argument("-v", "--value", help="value to assign to the TOML key path")
    parser.add_argument("input", help="input file")
    args = parser.parse_args()

    with open(args.input, "rb") as f:
        doc = tomlrt.load(f)

    if args.path:
        path = _parse_path(args.path)
        node = doc

        # Walk intermediate segments to reach the parent table. We stop one
        # short so we can index the final key for its value rather than
        # descending into it as a table.
        for segment in path[:-1]:
            node = node[segment]

        if args.value:
            # Write mode: set the value at the path, then emit the full modified
            # document. The caller controls where it lands via --output (file)
            # or stdout (default).
            node[path[-1]] = args.value
            result = tomlrt.dumps(doc)
        else:
            result = str(node[path[-1]])
    else:
        # No path specified — emit the entire document, preserving comments and
        # formatting via tomlrt's round-trip serialiser.
        result = tomlrt.dumps(doc)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
    else:
        sys.stdout.write(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
