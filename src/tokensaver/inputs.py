"""Turn a CLI argument into prompt text: a file path, '-' for stdin, or literal text."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# A single word with a file extension, or something with a path separator.
_LOOKS_LIKE_PATH = re.compile(r"^[^\s]+\.[A-Za-z0-9]{1,5}$|^[^\s]*[/\\][^\s]*$")


@dataclass(frozen=True)
class PromptInput:
    text: str
    source: str  # file name, "stdin" or "text"
    path: Path | None = None


def read_file(path: Path) -> str:
    """Read UTF-8 text, dropping a byte-order mark if an editor added one."""
    return path.read_text(encoding="utf-8-sig")


def resolve_input(value: str) -> PromptInput:
    """Interpret `value` as stdin ('-'), an existing file, or literal prompt text.

    Raises FileNotFoundError when the value looks like a path but the file is missing,
    so a typo in a file name is not silently counted as text.
    """
    if value == "-":
        return PromptInput(text=sys.stdin.read(), source="stdin")

    path = Path(value)
    if "\n" not in value and len(value) < 1024:
        try:
            is_file = path.is_file()
        except OSError:
            is_file = False
        if is_file:
            return PromptInput(text=read_file(path), source=path.name, path=path)
        if _LOOKS_LIKE_PATH.match(value):
            raise FileNotFoundError(f"File not found: {value}")
    return PromptInput(text=value, source="text")
