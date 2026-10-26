from tokensaver.optimizer import duplicates
from tokensaver.optimizer.base import Risk

PARA = "Answer only questions about our product catalogue and pricing."


def test_needs_review() -> None:
    assert duplicates.RISK is Risk.REVIEW


def test_removes_exact_duplicate_paragraph(apply_rule) -> None:
    text = f"{PARA}\n\nSecond paragraph that is unique enough.\n\n{PARA}"
    assert apply_rule(duplicates, text) == f"{PARA}\n\nSecond paragraph that is unique enough."


def test_duplicate_paragraph_ignores_case_and_spacing(apply_rule) -> None:
    text = f"{PARA}\n\n{PARA.upper()}  \n\nEnd of the prompt goes here."
    assert apply_rule(duplicates, text) == f"{PARA}\n\nEnd of the prompt goes here."


def test_flags_near_duplicate_paragraph() -> None:
    near = PARA.replace("questions", "question")
    [suggestion] = duplicates.find(f"{PARA}\n\n{near}")
    assert "Near-duplicate" in suggestion.title
    assert suggestion.see_line == 1


def test_different_paragraphs_are_kept() -> None:
    text = f"{PARA}\n\nWrite in a friendly tone and keep it short please."
    assert duplicates.find(text) == []


def test_removes_duplicate_line_inside_paragraph(apply_rule) -> None:
    text = "Rules:\n- Never share internal data.\n- Be brief.\n- Never share internal data."
    assert apply_rule(duplicates, text) == "Rules:\n- Never share internal data.\n- Be brief."


def test_short_lines_are_not_duplicates() -> None:
    assert duplicates.find("---\nA\n---\nB\n---") == []


def test_ignores_code_blocks() -> None:
    text = "```\nprint('the same line here ok')\nprint('the same line here ok')\n```"
    assert duplicates.find(text) == []


def test_line_inside_removed_paragraph_is_not_double_counted() -> None:
    text = f"{PARA}\n\n{PARA}"
    assert len(duplicates.find(text)) == 1
