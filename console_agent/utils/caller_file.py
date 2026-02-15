"""
Caller source file detection — automatically reads the source file
where agent() was called (or where an Error originated) and sends it
as context to the AI model.

Python equivalent of src/utils/caller-file.ts in the TypeScript SDK.
"""

from __future__ import annotations

import inspect
import os
import traceback
from dataclasses import dataclass
from typing import Optional

# ─── Types ────────────────────────────────────────────────────────────────────

MAX_FILE_SIZE = 100_000  # 100KB — truncate larger files

# Source file extensions to read
SOURCE_EXTENSIONS = {".py", ".pyx", ".pyi"}

# Patterns that indicate internal frames (skip these)
INTERNAL_PATTERNS = [
    "console_agent/",
    "console_agent\\",
    "/agno/",
    "\\agno\\",
    "/site-packages/",
    "\\site-packages\\",
    "/asyncio/",
    "\\asyncio\\",
    "/concurrent/",
    "\\concurrent\\",
    "/threading",
    "\\threading",
    "/importlib/",
    "\\importlib\\",
    "/runpy.py",
    "\\runpy.py",
    "<frozen",
    "<string>",
    "<module>",
]


@dataclass
class SourceFileInfo:
    """Information about a detected source file."""

    file_path: str
    file_name: str
    line: int
    column: int
    content: str
    function_name: Optional[str] = None


# ─── Stack Inspection ─────────────────────────────────────────────────────────


def _is_internal_frame(filename: str) -> bool:
    """Check if a stack frame is from internal/library code."""
    if not filename:
        return True
    for pattern in INTERNAL_PATTERNS:
        if pattern in filename:
            return True
    return False


def _is_source_file(filename: str) -> bool:
    """Check if a filename is a readable source file."""
    if not filename:
        return False
    _, ext = os.path.splitext(filename)
    return ext.lower() in SOURCE_EXTENSIONS


def _read_source_file(file_path: str) -> Optional[str]:
    """Read source file content with size limits."""
    try:
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(MAX_FILE_SIZE)
            return content + f"\n... (truncated — file is {size:,} bytes)"
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


# ─── Public API ───────────────────────────────────────────────────────────────


def get_caller_file(skip_frames: int = 0) -> Optional[SourceFileInfo]:
    """Detect the source file of the caller (where agent() was called).

    Walks up the call stack, skipping internal frames, to find the
    first external .py file.

    Args:
        skip_frames: Extra frames to skip beyond internal ones.

    Returns:
        SourceFileInfo if a valid external source file is found, else None.
    """
    stack = inspect.stack()

    # Skip frames: current function + internal console_agent frames
    skipped = 0
    for frame_info in stack:
        filename = frame_info.filename

        if _is_internal_frame(filename):
            continue

        if not _is_source_file(filename):
            continue

        if skipped < skip_frames:
            skipped += 1
            continue

        # Found an external source file
        content = _read_source_file(filename)
        if content is None:
            continue

        return SourceFileInfo(
            file_path=os.path.abspath(filename),
            file_name=os.path.basename(filename),
            line=frame_info.lineno,
            column=0,  # Python doesn't provide column info easily
            content=content,
            function_name=frame_info.function if frame_info.function != "<module>" else None,
        )

    return None


def get_error_source_file(error: BaseException) -> Optional[SourceFileInfo]:
    """Extract source file info from an exception's traceback.

    Parses the traceback to find the originating file (first non-internal
    frame from the bottom of the stack).

    Args:
        error: The exception to analyze.

    Returns:
        SourceFileInfo if the error's origin file can be read, else None.
    """
    tb = error.__traceback__
    if tb is None:
        return None

    # Walk the traceback to the innermost frame
    frames = traceback.extract_tb(tb)
    if not frames:
        return None

    # Look from the bottom (innermost) for the first non-internal frame
    for frame in reversed(frames):
        filename = frame.filename

        if _is_internal_frame(filename):
            continue

        if not _is_source_file(filename):
            continue

        content = _read_source_file(filename)
        if content is None:
            continue

        return SourceFileInfo(
            file_path=os.path.abspath(filename),
            file_name=os.path.basename(filename),
            line=frame.lineno,
            column=0,
            content=content,
            function_name=frame.name if frame.name != "<module>" else None,
        )

    return None


def format_source_for_context(source: SourceFileInfo) -> str:
    """Format source file content with line numbers and an arrow marker.

    The output highlights the relevant line with ``→`` and shows
    surrounding lines with their line numbers.

    Args:
        source: The source file info to format.

    Returns:
        Formatted string ready to include in the AI prompt.
    """
    lines = source.content.split("\n")
    total = len(lines)

    # Build line-numbered output with arrow marker
    numbered: list[str] = []
    for i, line_text in enumerate(lines, start=1):
        marker = " → " if i == source.line else "   "
        numbered.append(f"{marker}{i:>4} | {line_text}")

    header = f"--- Source File: {source.file_name} (line {source.line})"
    if source.function_name:
        header += f", in {source.function_name}"
    header += " ---"

    return header + "\n" + "\n".join(numbered)
