from tokensaver.optimizer import long_examples
from tokensaver.optimizer.base import Risk

LONG_BODY = "The customer wrote a long message about a delayed order. " * 20


def test_needs_review_and_never_edits() -> None:
    assert long_examples.RISK is Risk.REVIEW
    text = f"Example 1:\nInput: {LONG_BODY}\nOutput: ok"
    assert all(s.flag_only for s in long_examples.find(text))


def test_flags_long_marker_example() -> None:
    text = f"Task: classify.\n\nExample 1:\nInput: {LONG_BODY}\nOutput: delayed\n\nNow classify."
    [suggestion] = long_examples.find(text)
    assert suggestion.line == 3
    start, end = suggestion.span
    assert text[start:end].startswith("Example 1:")
    assert "Now classify" not in text[start:end]


def test_flags_long_xml_example() -> None:
    text = f"<example>\n{LONG_BODY}\n</example>"
    [suggestion] = long_examples.find(text)
    assert suggestion.span == (0, len(text))


def test_short_examples_are_fine() -> None:
    text = "Example 1:\nInput: hi\nOutput: greeting\n\nExample 2:\nInput: bye\nOutput: farewell"
    assert long_examples.find(text) == []


def test_flags_too_many_examples() -> None:
    blocks = [f"### Example {i}\nInput: {i}\nOutput: {i * 2}" for i in range(1, 6)]
    suggestions = long_examples.find("\n\n".join(blocks))
    [many] = suggestions
    assert "5 examples" in many.title
    assert many.line == 13  # fourth example


def test_examples_in_code_blocks_are_ignored() -> None:
    text = f"```\nExample:\n{LONG_BODY}\n```"
    assert long_examples.find(text) == []
