"""Minify pretty-printed JSON blocks.

Only whitespace outside strings is removed, so keys, values, number formats and even
duplicate keys stay exactly as written. Every result is re-parsed and compared.
"""

from __future__ import annotations

import json
import re

from tokensaver.optimizer.base import (
    Edit,
    Risk,
    Suggestion,
    code_fence_spans,
    line_number,
    overlaps,
)

NAME = "json"
RISK = Risk.SAFE

_JSON_START = re.compile(r"^[ \t]*[\[{]", re.MULTILINE)
_FENCE_BODY = re.compile(r"\A[ \t]*(`{3,}|~{3,})[^\n]*\n(?P<body>.*\n)[ \t]*\1[ \t]*\Z", re.DOTALL)
_DECODER = json.JSONDecoder()


def minify(json_text: str) -> str:
    """Remove whitespace outside JSON strings."""
    out: list[str] = []
    in_string = escaped = False
    for char in json_text:
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            out.append(char)
        elif char not in " \t\r\n":
            out.append(char)
    return "".join(out)


def _parse_exact(json_text: str) -> object:
    """Parse keeping literal number text and key order/duplicates, for comparison."""
    return json.loads(
        json_text,
        object_pairs_hook=lambda pairs: ("object", pairs),
        parse_float=lambda s: ("number", s),
        parse_int=lambda s: ("number", s),
        parse_constant=lambda s: ("constant", s),
    )


def _minified_if_safe(json_text: str) -> str | None:
    """Minified JSON, or None if it isn't a JSON object/array or nothing would change."""
    stripped = json_text.strip()
    if not stripped.startswith(("{", "[")):
        return None
    try:
        original = _parse_exact(stripped)
    except ValueError:
        return None
    small = minify(stripped)
    if small == stripped or _parse_exact(small) != original:
        return None
    return small


def _fenced_candidates(text: str, fences: list[tuple[int, int]]) -> list[Edit]:
    edits = []
    for start, end in fences:
        # Match on the slice: \A and \Z do not honour match()'s pos/endpos arguments.
        match = _FENCE_BODY.match(text[start:end])
        if not match:
            continue
        small = _minified_if_safe(match.group("body"))
        if small is not None:
            edits.append(Edit(start + match.start("body"), start + match.end("body"), small + "\n"))
    return edits


def _inline_candidates(text: str, fences: list[tuple[int, int]]) -> list[Edit]:
    edits: list[Edit] = []
    cursor = 0
    for match in _JSON_START.finditer(text):
        start = match.end() - 1
        if start < cursor or overlaps(start, start + 1, fences):
            continue
        try:
            _, end = _DECODER.raw_decode(text, start)
        except ValueError:
            continue
        line_end = text.find("\n", end)
        rest = text[end : len(text) if line_end == -1 else line_end]
        if rest.strip():
            continue  # JSON-looking text followed by prose; leave it alone
        small = _minified_if_safe(text[start:end])
        if small is not None:
            edits.append(Edit(start, end, small))
            cursor = end
    return edits


def find(text: str) -> list[Suggestion]:
    fences = code_fence_spans(text)
    edits = sorted(
        _fenced_candidates(text, fences) + _inline_candidates(text, fences),
        key=lambda e: e.start,
    )
    return [
        Suggestion(
            rule=NAME,
            risk=RISK,
            title=f"Minify JSON block ({len(edit.replacement)} chars, was {edit.end - edit.start})",
            reason="Indentation and spaces inside JSON cost tokens; the data is unchanged "
            "(verified by re-parsing).",
            line=line_number(text, edit.start),
            edits=(edit,),
        )
        for edit in edits
    ]
