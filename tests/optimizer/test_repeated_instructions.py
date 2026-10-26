from tokensaver.optimizer import repeated_instructions as rule
from tokensaver.optimizer.base import Risk


def test_needs_review() -> None:
    assert rule.RISK is Risk.REVIEW


def test_detects_reworded_instruction() -> None:
    text = "Always respond in JSON format.\nUse short keys.\nRemember to always respond in JSON."
    [suggestion] = rule.find(text)
    assert suggestion.line == 3
    assert suggestion.see_line == 1


def test_removes_whole_line_when_sentence_is_the_line(apply_rule) -> None:
    text = "- Never mention competitors.\n- Be concise.\n- Make sure you never mention competitors."
    assert apply_rule(rule, text) == "- Never mention competitors.\n- Be concise."


def test_removes_only_the_sentence_inside_a_line(apply_rule) -> None:
    text = "Never mention competitors.\nBe concise. Never mention competitors! Use lists."
    assert apply_rule(rule, text) == "Never mention competitors.\nBe concise. Use lists."


def test_different_instructions_are_kept() -> None:
    text = "Always respond in JSON.\nNever respond in XML or YAML.\nKeep answers short."
    assert rule.find(text) == []


def test_identical_lines_are_left_to_duplicates_rule() -> None:
    text = "Always respond in JSON format.\nAlways respond in JSON format."
    assert rule.find(text) == []


def test_non_instructions_are_ignored() -> None:
    text = "The report covers 2025 sales.\nThe report covers 2025 sales figures."
    assert rule.find(text) == []


def test_ignores_code_blocks() -> None:
    text = "Always use type hints.\n```\n# always use type hints\n```"
    assert rule.find(text) == []
