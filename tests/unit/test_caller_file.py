"""Unit tests for console_agent.utils.caller_file."""

import os
import tempfile

import pytest

from console_agent.utils.caller_file import (
    SourceFileInfo,
    format_source_for_context,
    get_caller_file,
    get_error_source_file,
    _is_internal_frame,
    _is_source_file,
    _read_source_file,
)


# ─── _is_internal_frame ──────────────────────────────────────────────────────


class TestIsInternalFrame:
    def test_console_agent_path_is_internal(self):
        assert _is_internal_frame("/path/to/console_agent/core.py") is True

    def test_site_packages_is_internal(self):
        assert _is_internal_frame("/venv/lib/python3.11/site-packages/agno/agent.py") is True

    def test_agno_path_is_internal(self):
        assert _is_internal_frame("/path/to/agno/models/google.py") is True

    def test_asyncio_is_internal(self):
        assert _is_internal_frame("/usr/lib/python3.11/asyncio/runners.py") is True

    def test_user_file_not_internal(self):
        assert _is_internal_frame("/home/user/project/billing.py") is False

    def test_empty_string_is_internal(self):
        assert _is_internal_frame("") is True

    def test_frozen_is_internal(self):
        assert _is_internal_frame("<frozen importlib._bootstrap>") is True

    # ─── Python REPL / interactive interpreter ────────────────────────────

    def test_stdin_is_internal(self):
        """Python interactive REPL uses <stdin> as filename."""
        assert _is_internal_frame("<stdin>") is True

    def test_console_is_internal(self):
        """Python code.InteractiveConsole uses <console> as filename."""
        assert _is_internal_frame("<console>") is True

    def test_input_is_internal(self):
        """Some REPLs use <input> as filename."""
        assert _is_internal_frame("<input>") is True

    def test_code_py_is_internal(self):
        """Python stdlib code.py (interactive console implementation) should be skipped."""
        assert _is_internal_frame("/usr/lib/python3.11/code.py") is True

    def test_codeop_py_is_internal(self):
        """Python stdlib codeop.py should be skipped."""
        assert _is_internal_frame("/usr/lib/python3.11/codeop.py") is True

    def test_ipython_is_internal(self):
        """IPython frames should be skipped."""
        assert _is_internal_frame("/venv/lib/python3.11/site-packages/IPython/core/interactiveshell.py") is True

    def test_ipykernel_is_internal(self):
        """Jupyter kernel frames should be skipped."""
        assert _is_internal_frame("/venv/lib/python3.11/site-packages/ipykernel/zmqshell.py") is True


# ─── _is_source_file ─────────────────────────────────────────────────────────


class TestIsSourceFile:
    def test_py_is_source(self):
        assert _is_source_file("billing.py") is True

    def test_pyi_is_source(self):
        assert _is_source_file("types.pyi") is True

    def test_pyx_is_source(self):
        assert _is_source_file("fast.pyx") is True

    def test_txt_not_source(self):
        assert _is_source_file("readme.txt") is False

    def test_js_not_source(self):
        assert _is_source_file("app.js") is False

    def test_empty_not_source(self):
        assert _is_source_file("") is False

    def test_no_extension_not_source(self):
        assert _is_source_file("Makefile") is False


# ─── _read_source_file ───────────────────────────────────────────────────────


class TestReadSourceFile:
    def test_reads_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("print('hello')\n")
            f.flush()
            content = _read_source_file(f.name)
        os.unlink(f.name)
        assert content == "print('hello')\n"

    def test_nonexistent_returns_none(self):
        assert _read_source_file("/nonexistent/path/file.py") is None

    def test_truncates_large_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x" * 200_000)
            f.flush()
            content = _read_source_file(f.name)
        os.unlink(f.name)
        assert content is not None
        assert "truncated" in content
        assert len(content) < 200_000


# ─── format_source_for_context ────────────────────────────────────────────────


class TestFormatSourceForContext:
    def test_basic_formatting(self):
        source = SourceFileInfo(
            file_path="/project/billing.py",
            file_name="billing.py",
            line=3,
            column=0,
            content="def calc():\n    x = 1\n    return x + 1\n",
            function_name="calc",
        )
        result = format_source_for_context(source)
        assert "billing.py" in result
        assert "line 3" in result
        assert "in calc" in result
        assert " → " in result  # arrow marker on line 3

    def test_arrow_on_correct_line(self):
        source = SourceFileInfo(
            file_path="/project/app.py",
            file_name="app.py",
            line=2,
            column=0,
            content="line1\nline2\nline3\n",
        )
        result = format_source_for_context(source)
        lines = result.split("\n")
        # Line 2 should have arrow
        arrow_lines = [l for l in lines if " → " in l]
        assert len(arrow_lines) == 1
        assert "line2" in arrow_lines[0]

    def test_no_function_name(self):
        source = SourceFileInfo(
            file_path="/project/app.py",
            file_name="app.py",
            line=1,
            column=0,
            content="x = 1\n",
        )
        result = format_source_for_context(source)
        assert "in " not in result.split("\n")[0]  # header line


# ─── get_error_source_file ────────────────────────────────────────────────────


class TestGetErrorSourceFile:
    def test_error_without_traceback_returns_none(self):
        err = ValueError("test")
        # No traceback attached
        assert get_error_source_file(err) is None

    def test_error_from_this_file(self):
        """Create a real traceback by catching an exception."""
        try:
            raise ValueError("intentional test error")
        except ValueError as e:
            result = get_error_source_file(e)

        # This test file should be detected as the source
        assert result is not None
        assert result.file_name == "test_caller_file.py"
        # content is the source file, so it includes its own source code
        assert "def test_error_from_this_file" in result.content
        assert result.line > 0


# ─── get_caller_file ─────────────────────────────────────────────────────────


class TestGetCallerFile:
    def test_detects_this_test_file(self):
        """get_caller_file should find this test file as the caller."""
        result = get_caller_file()
        # Should detect this test file (not internal console_agent code)
        assert result is not None
        assert result.file_name == "test_caller_file.py"
        assert "def test_detects_this_test_file" in result.content
