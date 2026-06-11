# tomlrt-cli

A command-line tool for reading and writing values in TOML files while preserving comments, formatting, and key ordering. Think `jq`, but for TOML.

## Why use this?

Most TOML libraries either can't write (Python's `tomllib`) or destroy comments and formatting when they do (`tomli-w`). `tomlrt-cli` uses a round-trip parser under the hood, so you can update a single value in a TOML file from a shell script or CI pipeline without mangling the rest of the document.

Common use cases:

* Bumping version numbers in `pyproject.toml` from CI
* Pinning container digests in config files
* Reading specific values for shell variable assignment
* Scripted config modifications that respect hand-crafted formatting

## Prerequisites

* Python 3.12 or newer
* [uv](https://docs.astral.sh/uv/) (for development and running from source)

No prerequisites for end users — install and run directly with `uvx`:

```bash
uvx tomlrt-cli --help
```

## Usage

### Read an entire file

```bash
tomlrt-cli config.toml
```

Outputs the full document to stdout (comments and formatting preserved).

### Read a specific value

```bash
tomlrt-cli --path project.version pyproject.toml
```

Outputs just the value at that path.

### Write a value (to stdout)

```bash
tomlrt-cli --path project.version --value "2.0.0" pyproject.toml
```

Outputs the full modified document to stdout. The original file is not changed.

### Write a value (to file)

```bash
tomlrt-cli --path project.version --value "2.0.0" --output pyproject.toml pyproject.toml
```

Writes the modified document to the output file. Use the same path for input and output to edit in-place.

### Path syntax

Keys are separated by dots. Keys that contain dots or special characters can be quoted or bracketed:

```bash
# Simple dotted path
tomlrt-cli --path version.v26.alpine config.toml

# Quoted key (key "3.14" contains a dot)
tomlrt-cli --path 'version."3.14".alpine' config.toml

# Bracket notation (same result)
tomlrt-cli --path 'version["3.14"].alpine' config.toml
```

All three notations are interchangeable and can be mixed in a single path.

### Flags

| Flag        | Short | Description                                 |
|-------------|-------|---------------------------------------------|
| `--path`    | `-p`  | TOML key path to read or write              |
| `--value`   | `-v`  | Value to assign at the given path           |
| `--output`  | `-o`  | Write result to this file (default: stdout) |
| `--version` | `-V`  | Print version and exit                      |
| `--help`    | `-h`  | Print help and exit                         |

## Development

### Setup

```bash
git clone <repo-url>
cd tomlrt-cli
uv sync
```

### Running tests

This project uses [Tryke](https://tryke.dev), a Rust-based test runner with a Jest-style API:

```bash
task test
```

The test suite has two files:

* `tests/test_cli.py` — Integration tests that exercise `main()` end-to-end with temporary TOML files. Verifies argument parsing, file I/O, and output routing.
* `tests/test_parse_path.py` — Unit tests for the path parser covering dotted, quoted, and bracket notation. Includes a [Hypothesis](https://hypothesis.readthedocs.io/) property test that fuzzes bare-key round-tripping to catch edge cases.

### Linting and formatting

```bash
task lint
```

### Build and publish

```bash
uv build       # Produces sdist + wheel in dist/
uv publish     # Upload to PyPI
```

## Troubleshooting

### `KeyError` when using `--path`

The path does not exist in the document. Double-check key names — TOML keys are case-sensitive. Run without `--path` to see the full document structure.

### Quoted keys not working

Make sure your shell isn't stripping the quotes. Wrap the entire `--path` value in single quotes:

```bash
tomlrt-cli --path 'version."3.14".alpine' config.toml
```

### `--value` didn't change the file

Without `--output`, changes go to stdout only. Add `--output <file>` to persist:

```bash
tomlrt-cli --path key --value new --output config.toml config.toml
```

### `ModuleNotFoundError: tomlrt`

Run via `uv run tomlrt-cli` (which manages the virtualenv) or install with `uv sync` first.
