"""Rule-based prompt optimizer.

Rules run in order. Each selected rule's edits are applied before the next rule
looks at the text, so no saving is counted twice.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from tokensaver.counter import count_tokens
from tokensaver.optimizer import (
    duplicates,
    filler,
    json_minify,
    long_examples,
    repeated_instructions,
    whitespace,
)
from tokensaver.optimizer.base import Edit, Risk, Suggestion, apply_edits, map_back
from tokensaver.pricing import ModelInfo, input_cost

# Whitespace runs after the rules that delete text, so it also tidies the gaps they leave.
RULES = (json_minify, duplicates, repeated_instructions, filler, whitespace, long_examples)
RULE_NAMES = tuple(rule.NAME for rule in RULES)


@dataclass(frozen=True)
class Finding:
    """A suggestion priced on a model.

    For editing suggestions `tokens`/`dollars` are the savings. For flag-only
    suggestions they are the cost of the flagged text (the most you could save).
    """

    suggestion: Suggestion
    tokens: int
    dollars: float
    applied: bool


@dataclass(frozen=True)
class OptimizationResult:
    model: ModelInfo
    original: str
    optimized: str
    findings: list[Finding]
    tokens_before: int
    tokens_after: int
    tidied: int = 0  # safe edits applied for neatness that saved no tokens

    @property
    def tokens_saved(self) -> int:
        return self.tokens_before - self.tokens_after

    @property
    def dollars_saved(self) -> float:
        return input_cost(self.tokens_saved, self.model)

    @property
    def percent_saved(self) -> float:
        return 100 * self.tokens_saved / self.tokens_before if self.tokens_before else 0.0


def resolve_selection(spec: str) -> frozenset[str]:
    """Turn 'safe', 'all', 'none' or a comma list of rule names into rule names."""
    value = spec.strip().lower()
    if value == "safe":
        return frozenset(rule.NAME for rule in RULES if rule.RISK is Risk.SAFE)
    if value == "all":
        return frozenset(RULE_NAMES)
    if value == "none":
        return frozenset()
    names = {part.strip() for part in value.split(",") if part.strip()}
    unknown = sorted(names - set(RULE_NAMES))
    if unknown:
        raise ValueError(
            f"Unknown rule(s): {', '.join(unknown)}. "
            f"Choose from: safe, all, none, {', '.join(RULE_NAMES)}"
        )
    return frozenset(names)


def _price(suggestion: Suggestion, text: str, model: ModelInfo, base_tokens: int) -> int:
    if suggestion.flag_only:
        start, end = suggestion.span or (0, 0)
        return count_tokens(text[start:end], model).tokens
    edited = apply_edits(text, suggestion.edits)
    return base_tokens - count_tokens(edited, model).tokens


def _remap_lines(old: str, new: str, edits: list[Edit], origin: list[int]) -> list[int]:
    """For each line of `new`, the original line number it came from."""
    remapped, offset = [], 0
    for line in new.split("\n"):
        old_offset = map_back(offset, edits)
        remapped.append(origin[old.count("\n", 0, old_offset)])
        offset += len(line) + 1
    return remapped


def _in_original_lines(suggestion: Suggestion, origin: list[int]) -> Suggestion:
    see_line = suggestion.see_line
    return replace(
        suggestion,
        line=origin[suggestion.line - 1],
        see_line=origin[see_line - 1] if see_line is not None else None,
    )


def optimize(
    text: str, model: ModelInfo, selected: frozenset[str] | None = None
) -> OptimizationResult:
    """Run every rule, applying edits only for rules in `selected` (default: safe rules)."""
    if selected is None:
        selected = resolve_selection("safe")
    original = text.replace("\r\n", "\n")
    current = original
    findings: list[Finding] = []
    tidied = 0
    origin = list(range(1, original.count("\n") + 2))  # current line -> original line

    for rule in RULES:
        suggestions = rule.find(current)
        if not suggestions:
            continue
        base_tokens = count_tokens(current, model).tokens
        apply = rule.NAME in selected
        to_apply = []
        for suggestion in suggestions:
            tokens = _price(suggestion, current, model, base_tokens)
            if tokens <= 0:
                # No saving on this tokenizer: keep it out of the list. Safe edits are
                # still applied so the output is tidy, and reported as a count.
                if apply and tokens == 0 and suggestion.risk is Risk.SAFE:
                    to_apply.append(suggestion)
                    tidied += len(suggestion.edits)
                continue
            to_apply.append(suggestion)
            findings.append(
                Finding(
                    suggestion=_in_original_lines(suggestion, origin),
                    tokens=tokens,
                    dollars=input_cost(tokens, model),
                    applied=apply and not suggestion.flag_only,
                )
            )
        if apply:
            edits = [edit for s in to_apply for edit in s.edits]
            edited = apply_edits(current, edits)
            origin = _remap_lines(current, edited, edits, origin)
            current = edited

    return OptimizationResult(
        model=model,
        original=original,
        optimized=current,
        findings=findings,
        tokens_before=count_tokens(original, model).tokens,
        tokens_after=count_tokens(current, model).tokens,
        tidied=tidied,
    )
