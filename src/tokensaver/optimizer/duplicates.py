"""Find duplicate and near-duplicate paragraphs, and duplicate lines."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from tokensaver.counter import count_raw
from tokensaver.optimizer.base import (
    Edit,
    Risk,
    Suggestion,
    drop_overlapping,
    line_number,
    overlaps,
    shorten,
)
from tokensaver.optimizer.fewshot import protected_spans

NAME = "duplicates"
RISK = Risk.REVIEW

# Lengths are measured in tokens, not characters, so dense scripts (Chinese, Korean,
# Japanese) are treated like English: a 13-character Chinese rule is a real instruction.
MIN_TOKENS = 5  # ignore short lines like "---" or "Thanks"
NEAR_MIN_TOKENS = 10
_TOKENIZER = "o200k_base"
NEAR_RATIO = 0.9
MAX_NEAR_COMPARISONS = 200_000

_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n\s*")


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _tokens(text: str) -> int:
    return count_raw(text, _TOKENIZER)


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for match in _PARAGRAPH_BREAK.finditer(text):
        spans.append((start, match.start()))
        start = match.end()
    spans.append((start, len(text)))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def _similarity(a: str, b: str) -> float:
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    if matcher.real_quick_ratio() < NEAR_RATIO or matcher.quick_ratio() < NEAR_RATIO:
        return 0.0
    return matcher.ratio()


def _paragraph_suggestions(text: str, fences: list[tuple[int, int]]) -> list[Suggestion]:
    spans = _paragraph_spans(text)
    kept: list[tuple[int, str]] = []  # (span index, normalized text)
    suggestions = []
    comparisons = 0
    for index, (start, end) in enumerate(spans):
        norm = _normalize(text[start:end])
        if overlaps(start, end, fences):
            continue
        size = _tokens(norm)
        if size < MIN_TOKENS:
            continue

        match_index, ratio = None, 0.0
        for kept_index, kept_norm in kept:
            if norm == kept_norm:
                match_index, ratio = kept_index, 1.0
                break
            if size >= NEAR_MIN_TOKENS and comparisons < MAX_NEAR_COMPARISONS:
                comparisons += 1
                score = _similarity(kept_norm, norm)
                if score >= NEAR_RATIO and score > ratio:
                    match_index, ratio = kept_index, score

        if match_index is None:
            kept.append((index, norm))
            continue

        # Remove the paragraph together with the blank line(s) that separate it.
        if index + 1 < len(spans):
            edit = Edit(start, spans[index + 1][0])
        else:
            edit = Edit(spans[index - 1][1], end)
        original_line = line_number(text, spans[match_index][0])
        kind = "Duplicate" if ratio == 1.0 else f"Near-duplicate ({ratio:.0%} similar)"
        suggestions.append(
            Suggestion(
                rule=NAME,
                risk=RISK,
                title=f"{kind} paragraph: “{shorten(text[start:end], 50)}”",
                reason="Repeats an earlier paragraph."
                + ("" if ratio == 1.0 else " Check whether the small differences matter."),
                line=line_number(text, start),
                edits=(edit,),
                see_line=original_line,
            )
        )
    return suggestions


def _line_suggestions(text: str, fences: list[tuple[int, int]]) -> list[Suggestion]:
    seen: dict[str, int] = {}
    suggestions = []
    offset = 0
    for number, line in enumerate(text.split("\n"), start=1):
        start, end = offset, offset + len(line)
        offset = end + 1
        norm = _normalize(line)
        if not norm or overlaps(start, end + 1, fences) or _tokens(norm) < MIN_TOKENS:
            continue
        if norm not in seen:
            seen[norm] = number
            continue
        edit = Edit(start, end + 1) if end < len(text) else Edit(max(start - 1, 0), end)
        suggestions.append(
            Suggestion(
                rule=NAME,
                risk=RISK,
                title=f"Duplicate line: “{shorten(line, 50)}”",
                reason="Same text as an earlier line.",
                line=number,
                edits=(edit,),
                see_line=seen[norm],
            )
        )
    return suggestions


def find(text: str) -> list[Suggestion]:
    protected = protected_spans(text)
    paragraphs = _paragraph_suggestions(text, protected)
    lines = _line_suggestions(text, protected)

    # Paragraph removals win; drop line removals that fall inside them.
    kept_edits = drop_overlapping([s.edits[0] for s in paragraphs] + [s.edits[0] for s in lines])
    kept = set(kept_edits)
    result = [s for s in paragraphs + lines if s.edits[0] in kept]
    return sorted(result, key=lambda s: s.line)
