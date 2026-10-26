import io

import pytest

from tokensaver.inputs import resolve_input


def test_existing_file_is_read(tmp_path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("Grüße 🚀", encoding="utf-8")
    result = resolve_input(str(path))
    assert result.text == "Grüße 🚀"
    assert result.source == "prompt.txt"
    assert result.path == path


def test_byte_order_mark_is_dropped(tmp_path) -> None:
    path = tmp_path / "bom.txt"
    path.write_bytes("\ufeffHello".encode())
    assert resolve_input(str(path)).text == "Hello"


def test_plain_text_is_used_as_is() -> None:
    result = resolve_input("Summarize this article in three bullets.")
    assert result.text == "Summarize this article in three bullets."
    assert result.source == "text"
    assert result.path is None


def test_multiline_text_is_not_treated_as_path() -> None:
    assert resolve_input("line one\nline two").text == "line one\nline two"


@pytest.mark.parametrize("value", ["missing.txt", "prompts/missing.md", "C:\\nope\\x.txt"])
def test_missing_file_is_an_error(value: str) -> None:
    with pytest.raises(FileNotFoundError, match="File not found"):
        resolve_input(value)


def test_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("from a pipe"))
    result = resolve_input("-")
    assert result.text == "from a pipe"
    assert result.source == "stdin"
