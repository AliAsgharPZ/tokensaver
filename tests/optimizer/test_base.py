import pytest

from tokensaver.optimizer.base import (
    Edit,
    apply_edits,
    code_fence_spans,
    drop_overlapping,
    line_number,
    shorten,
)


def test_apply_edits_in_any_order() -> None:
    edits = [Edit(6, 11, "there"), Edit(0, 5, "Hi")]
    assert apply_edits("hello world", edits) == "Hi there"


def test_apply_edits_rejects_overlap() -> None:
    with pytest.raises(ValueError, match="Overlapping"):
        apply_edits("hello", [Edit(0, 3), Edit(2, 4)])


def test_drop_overlapping_keeps_first() -> None:
    kept = drop_overlapping([Edit(0, 5), Edit(3, 8), Edit(5, 9)])
    assert kept == [Edit(0, 5), Edit(5, 9)]


def test_code_fence_spans() -> None:
    text = "intro\n```python\nx = 1\n```\nafter\n~~~\nraw\n~~~\n"
    spans = code_fence_spans(text)
    assert [text[s:e] for s, e in spans] == ["```python\nx = 1\n```", "~~~\nraw\n~~~"]


def test_unclosed_fence_is_ignored() -> None:
    assert code_fence_spans("```\nnever closed\n") == []


def test_line_number_and_shorten() -> None:
    assert line_number("a\nb\nc", 4) == 3
    assert shorten("a   b\nc") == "a b c"
    assert shorten("x" * 100, 10) == "x" * 9 + "…"


def test_shorten_counts_wide_characters_as_two_columns() -> None:
    # 10 columns: 4 wide characters (8 columns) + the ellipsis
    assert shorten("只回答与机票酒店预订相关的问题", 10) == "只回答与…"
    assert shorten("항상 JSON 형식으로", 9) == "항상 JSO…"  # 2+2+1+1+1+1 = 8 columns + "…"
    assert shorten("短文本", 10) == "短文本"  # 6 columns: fits, no ellipsis
    assert shorten("Grüße — naïve", 20) == "Grüße — naïve"  # accents are 1 column
