"""Locate few-shot examples ('Example 1:' blocks and <example> tags).

Rules that rewrite wording skip these spans: an example's exact text is part of what
it teaches the model.
"""

from __future__ import annotations

import re

from tokensaver.optimizer.base import code_fence_spans, overlaps

_XML_EXAMPLE = re.compile(r"<example\b[^>]*>.*?</example>", re.IGNORECASE | re.DOTALL)
_MARKER = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*)?(?:example|sample)(?:[ \t]*#?\d+)?(?:\*\*)?[ \t]*:?",
    re.IGNORECASE | re.MULTILINE,
)
_HEADING = re.compile(r"^[ \t]*#{1,6}[ \t]", re.MULTILINE)
_CONTINUATION = re.compile(
    r"^[ \t]*(?:input|output|q|a|question|answer|user|assistant|response|result|expected|"
    r"[-*•>]|\d+[.)]|[ \t])",
    re.IGNORECASE,
)


def _marker_block_end(text: str, start: int, stop: int) -> int:
    """End of an 'Example:' block: the next marker/heading, or a blank line followed by prose."""
    pos = text.find("\n", start)
    while 0 <= pos < stop:
        next_line_start = pos + 1
        rest = text[next_line_start:stop]
        if not rest.strip():
            return pos
        if _HEADING.match(rest) or _MARKER.match(rest):
            return pos
        if not text[next_line_start:].split("\n", 1)[0].strip():
            # Blank line: the block continues only if the next text still looks like an example.
            following = rest.lstrip("\n \t")
            if not _CONTINUATION.match(following):
                return pos
        pos = text.find("\n", next_line_start)
    return stop


def example_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of few-shot examples, outside code blocks, in order."""
    fences = code_fence_spans(text)
    spans = [m.span() for m in _XML_EXAMPLE.finditer(text)]
    markers = [
        m.start()
        for m in _MARKER.finditer(text)
        if not overlaps(m.start(), m.end(), fences) and not overlaps(m.start(), m.end(), spans)
    ]
    for index, start in enumerate(markers):
        stop = markers[index + 1] if index + 1 < len(markers) else len(text)
        spans.append((start, _marker_block_end(text, start, stop)))
    return sorted(spans)


def protected_spans(text: str) -> list[tuple[int, int]]:
    """Spans that wording rules must not edit: code blocks and few-shot examples."""
    return sorted(code_fence_spans(text) + example_spans(text))
