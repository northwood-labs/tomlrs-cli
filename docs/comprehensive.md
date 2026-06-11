# Deep Architecture Audit

## Entry points

| Entry point                | Mechanism                                  | Target                    |
|----------------------------|--------------------------------------------|---------------------------|
| `tomlrt-cli` shell command | `[project.scripts]` in `pyproject.toml`    | `tomlrt_cli.cli:main`     |
| `uvx tomlrt-cli`           | PyPI package resolution + same entry point | `tomlrt_cli.cli:main`     |
| `python -m tomlrt_cli.cli` | `if __name__ == "__main__"` guard          | `main()` via `sys.exit()` |

There is exactly one entry point function. All invocation methods converge on `main()`.

## CLI startup and initialization flow

1. Python runtime loads src/tomlrt_cli/cli.py
2. Module-level imports execute:
   * argparse, re, sys (stdlib)
   * tomlrt (third-party, Rust-backed TOML library)
3. main() is called by the entry point mechanism
4. argparse builds the parser with:
   * -V/--version (immediate exit with version string)
   * -o/--output (optional: file path for output)
   * -p/--path (optional: TOML key path to target)
   * -v/--value (optional: value to write at --path)
   * input (positional: source TOML file)
5. parser.parse_args() consumes sys.argv
6. Input file is opened in binary mode and passed to tomlrt.load()

No lazy loading, no plugin system, no configuration files. The startup path is deterministic and has no conditional imports.

## Command-specific flows

### Read entire document (no `--path`)

```text
tomlrt.load(input) → tomlrt.dumps(doc) → output
```

The document passes through tomlrt's round-trip serializer unchanged. Comments, whitespace, and key ordering are preserved.

### Read a specific value (`--path` without `--value`)

```text
tomlrt.load(input)
  → _parse_path(args.path) → tuple of key segments
  → Walk doc[seg1][seg2]...[segN-1]
  → Read doc[...][segN]
  → str() the value
  → output
```

The walk stops one segment short of the leaf so we can index the final key for its value rather than descending into it as a sub-table.

### Write a value (`--path` + `--value`)

```text
tomlrt.load(input)
  → _parse_path(args.path) → tuple of key segments
  → Walk to parent table
  → Assign args.value to the final key
  → tomlrt.dumps(doc) (full document with modification)
  → output
```

The value is always assigned as a string. The full modified document is serialized — not just the changed key — so that comments and structure are preserved.

### Output routing

```text
if args.output → open(args.output, "w").write(result)
else           → sys.stdout.write(result)
```

This is the final step regardless of which flow preceded it. The separation means `--value` without `--output` is a safe "preview" operation.

## File and module responsibilities

### `src/tomlrt_cli/__init__.py`

Package marker only. Contains a single docstring. Exists so Python recognizes `tomlrt_cli` as an importable package.

### `src/tomlrt_cli/cli.py`

| Section             | Responsibility                                                                    |
|---------------------|-----------------------------------------------------------------------------------|
| Module docstring    | Documents the module's role as the sole user interface                            |
| `_parse_path()`     | Converts human-friendly path notation into the tuple format tomlrt requires       |
| `main()`            | Orchestrates: parse args → load file → resolve path → read or write → emit output |
| `if __name__` guard | Enables direct script execution for development/debugging                         |

### `tests/test_cli.py`

Integration tests that exercise `main()` end-to-end with real temp files. Verifies the argument parser, file I/O, and output routing work together.

### `tests/test_parse_path.py`

Unit tests for `_parse_path()`. Covers each syntax variant (dotted, quoted, bracket) plus a hypothesis property test that fuzzes bare-key round-tripping.

## Decision points and side effects

### Decision: when does the tool write to disk?

Only when `--output` is explicitly provided. This is a deliberate safety choice — without it, the tool is read-only (stdout). Users must opt in to file mutation.

### Decision: path parsing lives in `cli.py`, not a separate module

The parser is ~30 lines. Extracting it to its own module would add import indirection without meaningful encapsulation benefit at this scale. If the parser grows (escape sequences, array indexing), it should be extracted.

### Decision: `tomlrt.load()` opens in binary mode

TOML files are UTF-8 by spec. Opening in binary mode (`"rb"`) lets tomlrt handle encoding internally, avoiding platform-specific text mode issues (e.g., Windows CRLF translation).

### Side effects

| Operation                            | Side effect                                                          |
|--------------------------------------|----------------------------------------------------------------------|
| `main()` with no `--output`          | Writes to stdout                                                     |
| `main()` with `--output`             | Creates or overwrites the output file                                |
| `main()` with `--value` + `--output` | Reads input, modifies in memory, writes to output (may be same file) |

### No side effects

* `_parse_path()` is pure — no I/O, no mutation, deterministic output.
* `tomlrt.load()` only reads; the file handle is closed immediately after.

## Risks, gaps, and follow-up inspections

### Risk: non-atomic file writes

**Current behavior:** `open(path, "w")` truncates the file before writing. If the process is interrupted between truncation and write completion, data is lost.

**Recommendation:** Write to a temporary file in the same directory, then `os.replace()` to the target path. This is atomic on POSIX filesystems.

### Risk: no error handling for missing keys

**Current behavior:** A `KeyError` propagates as an unhandled exception with a Python traceback.

**Recommendation:** Catch `KeyError` in the path-walk loop and emit a user-friendly error message with the failing segment and available keys.

### Risk: no type coercion for `--value`

**Current behavior:** Values are always written as TOML strings. `--value 42` produces `key = "42"`, not `key = 42`.

**Recommendation:** Add a `--type` flag (`string`, `int`, `float`, `bool`) or auto-detect from the value format.

### Gap: no `--create` / `--install` mode

`tomlrt` has `install()` which creates intermediate tables. The current CLI requires the full path to already exist. Adding an `--install` flag would enable creating new keys.

### Gap: no stdin support

The `input` argument is always a file path. Supporting `-` as stdin would enable piping.

### Gap: `--value` without `--path` is silently ignored

If a user passes `--value` but forgets `--path`, the value is never used and no warning is emitted.

### Follow-up inspection: tomlrt version pinning

`tomlrt>=1.7.2` is a minimum bound. A breaking change in tomlrt's API (e.g., `install()` signature change) would silently break the CLI. Consider an upper bound or lock file discipline.

## Design rationale

### Why a CLI wrapper around tomlrt?

Shell scripts and CI pipelines need to read and modify TOML files (version bumps, pin updates, config changes). Writing Python for each one-off mutation is overhead. A CLI tool lets these operations be single shell commands, composable with standard Unix tools.

### Why tomlrt specifically?

The defining requirement is **comment and formatting preservation**. Standard `tomllib` (stdlib) is read-only. `tomli-w` writes but discards comments. `tomlkit` preserves comments but has known bugs with certain table structures. `tomlrt` is Rust-backed, actively maintained, and handles the round-trip correctly.

### Why a custom path parser instead of using tomlrt's dotted-string splitting?

TOML keys can legally contain dots (e.g., `"3.14"` is a valid key). tomlrt's `install("a.b.c", val)` splits naively on `.`, making it impossible to target such keys via a dotted string. The custom parser gives users three ways to express the same path — dotted, quoted, or bracketed — and normalizes all of them to the tuple form that tomlrt handles unambiguously.

### Why argparse over click/typer?

The CLI has 4 flags and 1 positional argument. Click/typer would add a runtime dependency for decorator syntax that provides no benefit at this scale. argparse is stdlib, well-understood, and sufficient.

### Why tryke over pytest?

Tryke is Rust-powered with concurrent test execution by default. For a small test suite this is marginal, but it establishes the pattern for when the suite grows. The Jest-style `describe`/`test`/`expect` API is also more readable for behavior-oriented tests.

### Why hypothesis for a path parser?

The path parser has combinatorial input space (arbitrary nesting of dots, quotes, brackets). Example-based tests cover known cases; hypothesis finds the unknown ones — off-by-one errors, empty segments, adjacent delimiters — that a human wouldn't think to write.
