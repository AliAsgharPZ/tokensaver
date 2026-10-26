"""Shared types and text helpers for optimizer rules."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class Risk(str, Enum):
    SAFE = "safe"  # meaning cannot change; applied by default
    REVIEW = "review"  # probably fine, but a human should check


@dataclass(frozen=True)
class Edit:
    """Replace text[start:end] with `replacement`."""

    start: int
    end: int
    replacement: str = ""


@dataclass(frozen=True)
class Suggestion:
    rule: str
    risk: Risk
    title: str
    reason: str
    line: int
    edits: tuple[Edit, ...] = ()
    span: tuple[int, int] | None = None  # region a flag-only suggestion points at
    see_line: int | None = None  # related earlier line, e.g. the original of a duplicate

    @property
    def flag_only(self) -> bool:
        return not self.edits


def apply_edits(text: str, edits: Iterable[Edit]) -> str:
    """Apply non-overlapping edits to text."""
    parts: list[str] = []
    cursor = 0
    for edit in sorted(edits, key=lambda e: e.start):
        if edit.start < cursor:
            raise ValueError(f"Overlapping edit at offset {edit.start}")
        parts.append(text[cursor : edit.start])
        parts.append(edit.replacement)
        cursor = edit.end
    parts.append(text[cursor:])
    return "".join(parts)


def map_back(position: int, edits: Iterable[Edit]) -> int:
    """Map an offset in the edited text to the matching offset in the text before editing."""
    shift = 0
    for edit in sorted(edits, key=lambda e: e.start):
        new_start = edit.start + shift
        if position < new_start:
            break
        if position < new_start + len(edit.replacement):
            return edit.start
        shift += len(edit.replacement) - (edit.end - edit.start)
    return position - shift


def drop_overlapping(edits: Iterable[Edit]) -> list[Edit]:
    """Keep edits in the given priority order, skipping any that overlap a kept one."""
    kept: list[Edit] = []
    for edit in edits:
        if all(edit.end <= k.start or edit.start >= k.end for k in kept):
            kept.append(edit)
    return kept


_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$", re.MULTILINE | re.DOTALL)


def code_fence_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of fenced code blocks (``` or ~~~), fences included."""
    return [m.span() for m in _FENCE_RE.finditer(text)]


def overlaps(start: int, end: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(start < s_end and end > s_start for s_start, s_end in spans)


def line_number(text: str, index: int) -> int:
    """1-based line number of a character offset."""
    return text.count("\n", 0, index) + 1


def display_width(char: str) -> int:
    """Terminal columns a character takes: 2 for wide CJK characters, else 1."""
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def shorten(text: str, limit: int = 60) -> str:
    """One-line preview of text, at most `limit` terminal columns wide."""
    flat = " ".join(text.split())
    if sum(display_width(c) for c in flat) <= limit:
        return flat
    kept, used = [], 0
    for char in flat:
        used += display_width(char)
        if used > limit - 1:  # leave one column for the ellipsis
            break
        kept.append(char)
    return "".join(kept) + "…"
