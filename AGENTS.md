# Agent Guidance

This document orients AI agents working on `tomlrs-cli`. Read this first; it points to detailed references that you should load only when relevant to your current task.

## What this project is

A CLI tool that reads and writes TOML files with comment/formatting preservation. Think `jq` for TOML. Built on `tomlrt` (Rust-backed round-trip TOML library).

## Project layout

```text
src/tomlrs_cli/
  __init__.py        # Package marker (no logic)
  cli.py             # Sole module: arg parsing, path resolution, read/write
tests/
  test_cli.py        # Integration tests (main() end-to-end)
  test_parse_path.py # Unit tests for path parser + hypothesis property tests
docs/
  quickstart.md      # Quick flow summary
  comprehensive.md   # Deep architecture audit
```

## Technology stack

| Tool         | Purpose                                              | Invocation                                     |
|--------------|------------------------------------------------------|------------------------------------------------|
| `uv`         | Package manager, virtualenv, build, publish          | `uv sync`, `uv build`, `uv publish`            |
| `tomlrt`     | TOML parsing with comment/format preservation        | Runtime dependency                             |
| `ruff`       | Linting + formatting (replaces black, isort, flake8) | `uv run ruff check .` / `uv run ruff format .` |
| `zuban`      | Type checking (Rust-based, mypy-compatible)          | `uv run zuban check src/`                      |
| `tryke`      | Test runner (Rust-based, Jest-style API)             | `uv run tryke test`                            |
| `hypothesis` | Property-based testing                               | Used inside tryke tests via `@given`           |
| `kirograph`  | Semantic code graph (MCP server)                     | See `.kiro/steering/kirograph.md`              |

## Core rules

These are non-negotiable (from `.kiro/steering/core-premises.md`):

1. Don't assume. Don't hide confusion. Surface tradeoffs.
2. Minimum code that solves the problem. Nothing speculative.
3. Touch only what you must. Clean up only your own mess.
4. Define success criteria. Loop until verified.

## Verification workflow

After any code change:

1. `uv run ruff check .` — must pass with zero errors
2. `uv run ruff format --check .` — must report no changes needed
3. `uv run zuban check src/` — must report zero diagnostics
4. `uv run tryke test` — all tests must pass

Do not present work as finished while any check fails.

## Steering documents

Located in `.kiro/steering/`. These are automatically loaded based on their `inclusion` rules:

| File                         | When loaded                     | What it controls                              |
|------------------------------|---------------------------------|-----------------------------------------------|
| `core-premises.md`           | Always                          | Fundamental operating principles              |
| `kirograph.md`               | Always                          | KiroGraph tool usage guide                    |
| `python-code-conventions.md` | When editing `*.py` files       | Python style, type checking, formatting rules |
| `markdown-style.md`          | When editing `*.md` files       | Markdown formatting conventions               |
| `kirograph-review.md`        | Manual (code review tasks)      | Structured review workflow                    |
| `kirograph-debug.md`         | Manual (debugging tasks)        | Systematic debug workflow                     |
| `kirograph-refactor.md`      | Manual (refactoring tasks)      | Safe refactoring workflow                     |
| `kirograph-architecture.md`  | Manual (architecture questions) | Architecture exploration workflow             |
| `kirograph-onboard.md`       | Manual (understanding codebase) | Onboarding workflow                           |

To activate a manual steering file, read it directly when the task matches.

## Hooks

Located in `.kiro/hooks/`:

| Hook                                | Trigger               | Effect                                                  |
|-------------------------------------|-----------------------|---------------------------------------------------------|
| `kirograph-compress-hint.kiro.hook` | Before shell tool use | Reminds agent to use `kirograph_exec` for token savings |
| `kirograph-sync-if-dirty.kiro.hook` | Agent stop            | Syncs KiroGraph index with file changes                 |

## Agents

Located in `.kiro/agents/`:

| Agent            | Role                                                                      |
|------------------|---------------------------------------------------------------------------|
| `kirograph.json` | KiroGraph-aware agent with full MCP tool access for code graph operations |

## KiroGraph usage

This project has a `.kirograph/` directory. Use KiroGraph MCP tools instead of grep/glob/file reads:

* `kirograph_context(task: "...")` — Start here for any code task
* `kirograph_search(query: "...")` — Find symbols by name
* `kirograph_node(symbol: "...", includeCode: true)` — Read a symbol's source
* `kirograph_impact(symbol: "...")` — Check blast radius before editing
* `kirograph_exec(command: "...")` — Run shell commands with token compression

Full reference: `.kiro/steering/kirograph.md`

## Detailed references

Load these only when needed for the current task:

* **Python conventions**: `.kiro/steering/python-code-conventions.md` (style, types, imports, docstrings, section order)
* **Markdown style**: `.kiro/steering/markdown-style.md` (headings, lists, tables, code blocks)
* **Architecture details**: `docs/comprehensive.md` (flows, decisions, risks)
* **Quick orientation**: `docs/quickstart.md` (entry point, primary flow, module roles)
