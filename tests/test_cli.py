"""
Integration tests for the CLI entry point.

These verify that the argument parser, file I/O, and output routing work
together as a user would invoke them from a shell.
"""

import io
import sys
import tempfile
from contextlib import redirect_stdout

from tryke import describe, expect, test

from tomlrt_cli.cli import main

SAMPLE_TOML = """\
# A comment that should survive round-trips
[project]
name = "test"
version = "1.0.0"

[project.nested]
key = "deep"
"""


def _run(*args: str) -> tuple[int, str]:
    """
    Run main() with the given argv and capture stdout.
    Returns (exit_code, stdout_content).
    """
    sys.argv = ["tomlrt-cli", *args]
    buf = io.StringIO()

    with redirect_stdout(buf):
        code = main()

    return code, buf.getvalue()


def _tmpfile(content: str = SAMPLE_TOML) -> str:
    """
    Write content to a temp file and return its path.
    """
    f = tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False)
    f.write(content)
    f.flush()
    f.close()

    return f.name


with describe("read entire document"):

    @test("outputs full document to stdout")
    def test_full_document():
        path = _tmpfile()
        code, out = _run(path)
        expect(code).to_equal(0)
        expect(out).to_contain('[project]')
        expect(out).to_contain('name = "test"')

    @test("preserves comments in output")
    def test_preserves_comments():
        # Round-trip preservation is the core value proposition.
        path = _tmpfile()
        code, out = _run(path)
        expect(code).to_equal(0)
        expect(out).to_contain("# A comment that should survive round-trips")


with describe("read a specific value with --path"):

    @test("reads a top-level key")
    def test_read_top_level():
        path = _tmpfile()
        code, out = _run("--path", "project.name", path)
        expect(code).to_equal(0)
        expect(out).to_equal("test")

    @test("reads a nested key")
    def test_read_nested():
        path = _tmpfile()
        code, out = _run("--path", "project.nested.key", path)
        expect(code).to_equal(0)
        expect(out).to_equal("deep")

    @test("non-existent path raises KeyError")
    def test_missing_path():
        path = _tmpfile()
        sys.argv = ["tomlrt-cli", "--path", "does.not.exist", path]

        expect(lambda: main()).to_raise(KeyError)


with describe("write with --value"):

    @test("--value without --output writes modified document to stdout")
    def test_value_to_stdout():
        # The "preview" behavior — user can inspect before persisting.
        path = _tmpfile()
        code, out = _run("--path", "project.version", "--value", "2.0.0", path)
        expect(code).to_equal(0)
        expect(out).to_contain('version = "2.0.0"')

    @test("--value with --output writes to file")
    def test_value_to_file():
        path = _tmpfile()
        code, _ = _run(
            "--path",
            "project.version",
            "--value",
            "2.0.0",
            "--output",
            path,
            path,
        )
        expect(code).to_equal(0)

        with open(path) as f:
            content = f.read()

        expect(content).to_contain('version = "2.0.0"')

    @test("--value preserves comments after write")
    def test_value_preserves_comments():
        # Confirms the round-trip serializer doesn't strip comments
        # when a value is modified.
        path = _tmpfile()
        code, out = _run("--path", "project.name", "--value", "new", path)
        expect(code).to_equal(0)
        expect(out).to_contain("# A comment that should survive round-trips")

    @test("--value without --path is silently ignored")
    def test_value_without_path():
        # Documents current behavior: --value alone has no effect.
        path = _tmpfile()
        code, out = _run("--value", "ignored", path)
        expect(code).to_equal(0)
        expect(out).to_contain('name = "test"')


with describe("--output without --value"):

    @test("writes full document to output file")
    def test_output_full_doc():
        src = _tmpfile()
        dst = _tmpfile("")
        code, _ = _run("--output", dst, src)
        expect(code).to_equal(0)

        with open(dst) as f:
            content = f.read()

        expect(content).to_contain('[project]')
        expect(content).to_contain('name = "test"')


with describe("error cases"):

    @test("non-existent input file raises FileNotFoundError")
    def test_missing_file():
        sys.argv = ["tomlrt-cli", "/tmp/does_not_exist_xyz.toml"]

        expect(lambda: main()).to_raise(FileNotFoundError)
