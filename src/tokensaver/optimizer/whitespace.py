"""Remove trailing whitespace and extra blank lines. Code blocks are left untouched.

Spaces inside a line are kept on purpose: they can carry meaning in aligned tables.
"""

from __future__ import annotations

from tokensaver.optimizer.base import Edit, Risk, Suggestion, code_fence_spans, overlaps

NAME = "whitespace"
RISK = Risk.SAFE


def _line_starts(lines: list[str]) -> list[int]:
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line) + 1
    return starts


def find(text: str) -> list[Suggestion]:
    lines = text.split("\n")
    starts = _line_starts(lines)
    fences = code_fence_spans(text)

    def is_blank(i: int) -> bool:
        return not lines[i].strip() and not overlaps(starts[i], starts[i] + 1, fences)

    trailing: list[Edit] = []
    runs: list[Edit] = []
    ends: list[Edit] = []

    i = 0
    while i < len(lines):
        if not is_blank(i):
            line_start = starts[i]
            stripped = lines[i].rstrip(" \t")
            if len(stripped) < len(lines[i]) and not overlaps(line_start, line_start + 1, fences):
                trailing.append(Edit(line_start + len(stripped), line_start + len(lines[i])))
            i += 1
            continue

        j = i
        while j < len(lines) and is_blank(j):
            j += 1
        if i == 0 and j == len(lines):
            break  # text is only whitespace
        if i == 0:
            ends.append(Edit(0, starts[j]))
        elif j == len(lines):
            ends.append(Edit(starts[i] - 1, len(text)))
        elif j - i >= 2:
            runs.append(Edit(starts[i], starts[j], "\n"))
        elif lines[i]:
            trailing.append(Edit(starts[i], starts[i] + len(lines[i])))
        i = j

    suggestions = []
    if trailing:
        suggestions.append(
            Suggestion(
                rule=NAME,
                risk=RISK,
                title=f"Remove trailing spaces/tabs on {len(trailing)} line(s)",
                reason="Invisible whitespace at line ends costs tokens and carries no meaning.",
                line=text.count("\n", 0, trailing[0].start) + 1,
                edits=tuple(trailing),
            )
        )
    if runs:
        suggestions.append(
            Suggestion(
                rule=NAME,
                risk=RISK,
                title=f"Collapse {len(runs)} run(s) of blank lines",
                reason="One blank line separates sections just as well as several.",
                line=text.count("\n", 0, runs[0].start) + 1,
                edits=tuple(runs),
            )
        )
    if ends:
        suggestions.append(
            Suggestion(
                rule=NAME,
                risk=RISK,
                title="Trim blank lines at the start and end",
                reason="Leading and trailing blank lines are never needed.",
                line=text.count("\n", 0, ends[0].start) + 1,
                edits=tuple(ends),
            )
        )
    return suggestions
