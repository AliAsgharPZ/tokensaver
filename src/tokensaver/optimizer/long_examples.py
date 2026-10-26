"""Flag long few-shot examples and prompts with many examples. Never edits text."""

from __future__ import annotations

from tokensaver.counter import count_raw
from tokensaver.optimizer.base import Risk, Suggestion, line_number
from tokensaver.optimizer.fewshot import example_spans

NAME = "long-examples"
RISK = Risk.REVIEW

LONG_EXAMPLE_TOKENS = 150
MAX_EXAMPLES = 3
_TOKENIZER = "o200k_base"


def find(text: str) -> list[Suggestion]:
    spans = example_spans(text)
    suggestions = []
    for start, end in spans:
        tokens = count_raw(text[start:end], _TOKENIZER)
        if tokens > LONG_EXAMPLE_TOKENS:
            suggestions.append(
                Suggestion(
                    rule=NAME,
                    risk=RISK,
                    title=f"Long example (~{tokens} tokens)",
                    reason=f"Examples over ~{LONG_EXAMPLE_TOKENS} tokens are rarely needed; "
                    "a shorter example usually shows the pattern just as well.",
                    line=line_number(text, start),
                    span=(start, end),
                )
            )
    if len(spans) > MAX_EXAMPLES:
        extra = len(spans) - MAX_EXAMPLES
        extra_start, extra_end = spans[MAX_EXAMPLES][0], spans[-1][1]
        suggestions.append(
            Suggestion(
                rule=NAME,
                risk=RISK,
                title=f"{len(spans)} examples found",
                reason=f"{MAX_EXAMPLES} well-chosen examples are usually enough; the tokens "
                f"shown are what the extra {extra} cost{'s' if extra == 1 else ''}.",
                line=line_number(text, extra_start),
                span=(extra_start, extra_end),
            )
        )
    return suggestions
