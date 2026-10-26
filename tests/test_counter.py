import socket

import pytest
import tiktoken

from tokensaver import counter
from tokensaver.counter import count_raw, count_tokens, get_encoding
from tokensaver.pricing import load_prices

SAMPLES = {
    "empty": "",
    "hello": "Hello, world!",
    "special": "Text with <|endoftext|> inside",
    "unicode": "Grüße aus Köln — 東京 🚀 naïve café",
    "code": 'def f(x):\n    return {"a": [1, 2, 3]}\n\n\n',
    "spaces": "a    b\t\tc\n\n\n\nd   ",
}

# Produced by the official tiktoken.get_encoding() loader (tiktoken 0.14).
GOLDEN = {
    "o200k_base": {"empty": 0, "hello": 4, "special": 10, "unicode": 12, "code": 19, "spaces": 8},
    "cl100k_base": {"empty": 0, "hello": 4, "special": 9, "unicode": 16, "code": 19, "spaces": 8},
}


@pytest.mark.parametrize("encoding", sorted(GOLDEN))
@pytest.mark.parametrize("sample", sorted(SAMPLES))
def test_bundled_encoding_matches_official_counts(encoding: str, sample: str) -> None:
    assert count_raw(SAMPLES[sample], encoding) == GOLDEN[encoding][sample]


def test_counting_needs_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_network(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", no_network)
    get_encoding.cache_clear()
    assert count_raw("offline check", "o200k_base") > 0


def test_unknown_tokenizer_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported tokenizer"):
        get_encoding("p50k_base")


def test_corrupted_encoding_file_is_detected(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "o200k_base.tiktoken").write_bytes(b"dGVzdA== 0\n")
    monkeypatch.setattr(counter, "ENCODINGS_DIR", tmp_path)
    get_encoding.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="corrupted"):
            get_encoding("o200k_base")
    finally:
        get_encoding.cache_clear()


def test_exact_model_returns_raw_count() -> None:
    model = load_prices().get("gpt-4o")
    result = count_tokens("Hello, world!", model)
    assert result.tokens == 4
    assert result.exact is True
    assert result.model == "gpt-4o"


def test_estimated_model_scales_and_is_labelled() -> None:
    model = load_prices().get("claude-opus-5-5")
    text = "Hello, world! " * 50
    raw = count_raw(text, model.tokenizer)
    result = count_tokens(text, model)
    assert result.exact is False
    assert result.tokens == round(raw * model.estimate_factor)


def test_exact_models_match_tiktoken_model_map() -> None:
    """A model may only claim exact counts if tiktoken maps it to the same encoding."""
    for model in load_prices().models.values():
        if model.exact:
            assert tiktoken.encoding_name_for_model(model.name) == model.tokenizer, model.name
