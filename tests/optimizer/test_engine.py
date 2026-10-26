import pytest

from tokensaver.optimizer import RULE_NAMES, optimize, resolve_selection
from tokensaver.pricing import input_cost, load_prices

MESSY = (
    "\n\nI would like you to please summarize the text below.   \n"
    "Always respond in JSON format.\n\n\n\n"
    '{\n    "name": "string",\n    "tags": [\n        "a",\n        "b"\n    ]\n}\n\n'
    "Remember to always respond in JSON.\n\nThanks in advance!\n\n\n"
)


@pytest.fixture
def gpt4o():
    return load_prices().get("gpt-4o")


def test_rule_names_are_unique() -> None:
    assert len(set(RULE_NAMES)) == len(RULE_NAMES) == 6


def test_resolve_selection() -> None:
    assert resolve_selection("safe") == {"json", "whitespace"}
    assert resolve_selection("ALL") == set(RULE_NAMES)
    assert resolve_selection("none") == set()
    assert resolve_selection("filler, json") == {"filler", "json"}
    with pytest.raises(ValueError, match="Unknown rule"):
        resolve_selection("filler,nope")


def test_default_applies_only_safe_rules(gpt4o) -> None:
    result = optimize(MESSY, gpt4o)
    assert "I would like you to" in result.optimized
    assert '{"name":"string","tags":["a","b"]}' in result.optimized
    for finding in result.findings:
        assert finding.applied == (finding.suggestion.risk.value == "safe")


def test_all_rules_apply_review_suggestions(gpt4o) -> None:
    result = optimize(MESSY, gpt4o, resolve_selection("all"))
    assert result.optimized == (
        "Summarize the text below.\nAlways respond in JSON format.\n\n"
        '{"name":"string","tags":["a","b"]}'
    )


def test_zero_saving_safe_edits_are_applied_and_counted(gpt4o) -> None:
    result = optimize("Intro\n\n\n\nBody", gpt4o)
    assert result.optimized == "Intro\n\nBody"
    assert result.tidied == 1
    assert result.findings == []  # not listed as a saving


def test_zero_saving_safe_edits_respect_selection(gpt4o) -> None:
    result = optimize("Intro\n\n\n\nBody", gpt4o, resolve_selection("none"))
    assert result.optimized == "Intro\n\n\n\nBody"
    assert result.tidied == 0


def test_totals_are_measured_and_priced(gpt4o) -> None:
    result = optimize(MESSY, gpt4o, resolve_selection("all"))
    assert result.tokens_saved > 0
    assert result.tokens_after < result.tokens_before
    assert result.dollars_saved == pytest.approx(input_cost(result.tokens_saved, gpt4o))
    assert 0 < result.percent_saved < 100


def test_findings_all_save_tokens(gpt4o) -> None:
    for finding in optimize(MESSY, gpt4o, resolve_selection("all")).findings:
        assert finding.tokens > 0
        assert finding.dollars == pytest.approx(input_cost(finding.tokens, gpt4o))


def test_none_selected_leaves_text_unchanged(gpt4o) -> None:
    result = optimize(MESSY, gpt4o, resolve_selection("none"))
    assert result.optimized == MESSY
    assert result.tokens_saved == 0
    assert result.findings  # suggestions are still reported
    assert not any(f.applied for f in result.findings)


def test_windows_line_endings_are_normalized(gpt4o) -> None:
    result = optimize("Hello\r\nworld\r\n", gpt4o)
    assert result.original == "Hello\nworld\n"
    assert "\r" not in result.optimized


def test_clean_prompt_has_no_findings(gpt4o) -> None:
    result = optimize("Summarize the text in three bullet points.", gpt4o)
    assert result.findings == []
    assert result.percent_saved == 0


def test_line_numbers_refer_to_the_original_text(gpt4o) -> None:
    pretty = '{\n  "a": 1,\n  "b": 2\n}'  # lines 1-4, minified to one line first
    text = f"{pretty}\nAlways reply in English please.\nAgain: always reply in English."
    result = optimize(text, gpt4o, resolve_selection("all"))
    [repeated] = [f for f in result.findings if f.suggestion.rule == "repeated-instructions"]
    assert repeated.suggestion.line == 6
    assert repeated.suggestion.see_line == 5


def test_map_back() -> None:
    from tokensaver.optimizer.base import Edit, map_back

    # "01234567890" -> "01X567abc890": inserted text maps to its insertion point.
    edits = [Edit(2, 5, "X"), Edit(8, 8, "abc")]
    positions = (0, 2, 3, 5, 6, 8, 9, 11)
    assert [map_back(p, edits) for p in positions] == [0, 2, 5, 7, 8, 8, 8, 10]


def test_empty_prompt(gpt4o) -> None:
    result = optimize("", gpt4o)
    assert result.tokens_before == 0
    assert result.percent_saved == 0.0
