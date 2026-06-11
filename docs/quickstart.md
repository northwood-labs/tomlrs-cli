# Quick Flow Summary

## Entry point

```text
pyproject.toml → [project.scripts] → tomlrt_cli.cli:main
```

The CLI is invoked as `tomlrt-cli` (or `uvx tomlrt-cli`). Python's entry point mechanism calls `main()` in `src/tomlrt_cli/cli.py`.

## Primary flow

```text
User invokes CLI
  → argparse parses flags and positional input file
  → tomlrt loads the TOML file (preserving comments/formatting)
  → If --path is given:
      → _parse_path() converts the user string into a tuple of key segments
      → Walk the document to the target key
      → If --value is given:
          → Set the value at that key
          → Serialize the full modified document
      → Else:
          → Read and stringify the value at that key
  → Else:
      → Serialize the entire document
  → If --output is given:
      → Write result to that file
  → Else:
      → Write result to stdout
```

## Module roles

| Module                       | Role                                                                                  |
|------------------------------|---------------------------------------------------------------------------------------|
| `src/tomlrt_cli/__init__.py` | Package marker. No logic.                                                             |
| `src/tomlrt_cli/cli.py`      | Sole user-facing module. Argument parsing, path resolution, read/write orchestration. |

## Design decisions

| Decision                           | Rationale                                                                                                                                                                                                                         |
|------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Single-module CLI                  | The tool does one thing (read/write TOML paths). A single module keeps the dependency graph flat and the mental model simple.                                                                                                     |
| `tomlrt` for TOML handling         | Round-trip preservation of comments and formatting. Users can modify a value without destroying their hand-crafted TOML layout.                                                                                                   |
| Custom path parser (`_parse_path`) | `tomlrt` splits dotted strings naively on `.`, which breaks for keys containing dots (e.g., `"3.14"`). The parser lets users express these with quoting or bracket notation while producing the tuple `tomlrt` needs.             |
| `--output` controls file write     | Separates the "modify" concern from the "persist" concern. Without `--output`, changes go to stdout — safe for piping, previewing, or composing with other tools. With `--output`, the caller explicitly opts into file mutation. |
| `argparse` over click/typer        | Zero runtime dependencies beyond `tomlrt`. The CLI surface is small enough that argparse is sufficient.                                                                                                                           |
| `tryke` + `hypothesis` for testing | Tryke gives fast concurrent test execution. Hypothesis provides property-based coverage for the path parser, catching edge cases that example-based tests miss.                                                                   |
| `ruff` for linting/formatting      | Single tool replaces flake8 + isort + black. Fast, zero-config for common cases.                                                                                                                                                  |
| `zuban` for type checking          | Rust-based, mypy-compatible. Fast feedback loop during development.                                                                                                                                                               |

## Risks and unknowns

| Risk                                                         | Impact                                                                       | Mitigation                                                                                                                                    |
|--------------------------------------------------------------|------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `--value` only assigns strings                               | Users cannot set integers, booleans, or arrays from the CLI today.           | Future: add type coercion or a `--type` flag.                                                                                                 |
| No atomic write                                              | If the process is killed mid-write to `--output`, the file may be truncated. | Future: write to a temp file and rename (atomic on POSIX).                                                                                    |
| Path parser doesn't handle escape sequences                  | `\"` inside a quoted key would break the parser.                             | Acceptable for now — TOML bare/quoted keys rarely need escapes.                                                                               |
| `_parse_path` is exposed as `_`-prefixed but tested directly | Coupling tests to a private function.                                        | Acceptable trade-off: the parser is complex enough to warrant direct unit tests. If it moves to its own module later, tests follow trivially. |
| No validation of `--path` against the document               | A typo in the path produces a `KeyError` traceback, not a friendly message.  | Future: catch `KeyError` and emit a user-facing error.                                                                                        |
