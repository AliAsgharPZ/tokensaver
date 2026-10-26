"""Detect instructions that are given more than once, even with different wording."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

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

NAME = "repeated-instructions"
RISK = Risk.REVIEW

SIMILARITY = 0.8
MIN_WORDS = 3

_BULLET = re.compile(r"^[ \t]*(?:[-*•]|\d+[.)])[ \t]+")
_SENTENCE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
_LEAD_INS = re.compile(
    r"^(?:(?:important|note|reminder|again|also|and|so)\b[:,]?\s*"
    r"|please\s+|(?:always\s+)?remember(?:\s+to)?\s+|make\s+sure(?:\s+to|\s+that|\s+you)?\s+"
    r"|be\s+sure\s+to\s+|don'?t\s+forget\s+to\s+|once\s+again,?\s+)+"
)
_INSTRUCTION = re.compile(
    r"^(?:always|never|do|don'?t|dont|ensure|avoid|only|keep|use|respond|answer|reply|"
    r"return|write|include|format|output|provide|limit|follow|be|you\s+(?:must|should)|"
    r"must|should)\b|\b(?:must|should|never|always|do not)\b"
)


@dataclass(frozen=True)
class _Sentence:
    start: int
    end: int
    text: str
    norm: str
    whole_line: Edit | None  # removal edit when the sentence is its line's only content
    line_text: str


def _normalize(sentence: str) -> str:
    lowered = re.sub(r"[^\w\s']", " ", sentence.lower())
    lowered = " ".join(lowered.split())
    return _LEAD_INS.sub("", lowered).strip()


def _sentences(text: str) -> list[_Sentence]:
    fences = protected_spans(text)
    found = []
    offset = 0
    for line in text.split("\n"):
        line_start, line_end = offset, offset + len(line)
        offset = line_end + 1
        if not line.strip() or overlaps(line_start, line_end + 1, fences):
            continue
        bullet = _BULLET.match(line)
        body_start = bullet.end() if bullet else 0
        parts = [m for m in _SENTENCE.finditer(line, body_start) if m.group().strip()]
        for part in parts:
            norm = _normalize(part.group())
            if len(norm.split()) < MIN_WORDS or not _INSTRUCTION.search(norm):
                continue
            whole_line = None
            if len(parts) == 1:
                whole_line = (
                    Edit(line_start, line_end + 1)
                    if line_end < len(text)
                    else Edit(max(line_start - 1, 0), line_end)
                )
            lead = len(part.group()) - len(part.group().lstrip())
            found.append(
                _Sentence(
                    start=line_start + part.start() + lead,
                    end=line_start + part.end(),
                    text=part.group().strip(),
                    norm=norm,
                    whole_line=whole_line,
                    line_text=line.strip(),
                )
            )
    return found


def _same_line(a: _Sentence, b: _Sentence) -> bool:
    return " ".join(a.line_text.lower().split()) == " ".join(b.line_text.lower().split())


def _sentence_edit(text: str, sentence: _Sentence) -> Edit:
    if sentence.whole_line:
        return sentence.whole_line
    end = sentence.end
    while end < len(text) and text[end] in " \t":
        end += 1
    return Edit(sentence.start, end)


def find(text: str) -> list[Suggestion]:
    sentences = _sentences(text)
    candidates: list[tuple[Edit, Suggestion]] = []
    for index, later in enumerate(sentences):
        for earlier in sentences[:index]:
            if _same_line(earlier, later):
                continue  # identical lines are reported by the duplicates rule
            ratio = SequenceMatcher(None, earlier.norm, later.norm).ratio()
            if ratio < SIMILARITY:
                continue
            edit = _sentence_edit(text, later)
            first_line = line_number(text, earlier.start)
            candidates.append(
                (
                    edit,
                    Suggestion(
                        rule=NAME,
                        risk=RISK,
                        title=f"Repeated instruction: “{shorten(later.text, 50)}”",
                        reason=f"Says the same as “{shorten(earlier.text, 50)}”. "
                        "Stating it once is enough.",
                        line=line_number(text, later.start),
                        edits=(edit,),
                        see_line=first_line,
                    ),
                )
            )
            break

    kept = set(drop_overlapping(edit for edit, _ in candidates))
    return [suggestion for edit, suggestion in candidates if edit in kept]
