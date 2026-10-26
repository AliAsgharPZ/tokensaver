from tokensaver.optimizer import whitespace
from tokensaver.optimizer.base import Risk


def test_is_safe() -> None:
    assert whitespace.RISK is Risk.SAFE


def test_removes_trailing_spaces(apply_rule) -> None:
    assert apply_rule(whitespace, "one  \ntwo\t\nthree") == "one\ntwo\nthree"


def test_collapses_blank_line_runs(apply_rule) -> None:
    assert apply_rule(whitespace, "a\n\n\n\nb\n \n\t\nc") == "a\n\nb\n\nc"


def test_single_whitespace_only_line_is_emptied(apply_rule) -> None:
    assert apply_rule(whitespace, "a\n   \nb") == "a\n\nb"


def test_trims_start_and_end(apply_rule) -> None:
    assert apply_rule(whitespace, "\n\n  \nhello\nworld\n\n\n") == "hello\nworld"


def test_keeps_indentation_and_inner_spaces(apply_rule) -> None:
    text = "list:\n    - item   with   gaps\n\tTabbed"
    assert apply_rule(whitespace, text) == text


def test_leaves_code_blocks_untouched(apply_rule) -> None:
    text = "Code:\n```\nx = 1   \n\n\n\ny = 2\n```\nend  "
    assert apply_rule(whitespace, text) == "Code:\n```\nx = 1   \n\n\n\ny = 2\n```\nend"


def test_clean_text_has_no_suggestions() -> None:
    assert whitespace.find("Already\n\nclean") == []
    assert whitespace.find("") == []
    assert whitespace.find("   \n\n") == []


def test_suggestions_are_grouped_by_kind() -> None:
    titles = [s.title for s in whitespace.find("\n\na  \nb  \n\n\n\nc\n\n")]
    assert len(titles) == 3
    assert "2 line(s)" in titles[0]
