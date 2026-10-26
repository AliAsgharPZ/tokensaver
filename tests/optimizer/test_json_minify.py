import json

from tokensaver.optimizer import json_minify
from tokensaver.optimizer.base import Risk

PRETTY = '{\n    "name": "Ada Lovelace",\n    "tags": [\n        "math",\n        "code"\n    ]\n}'


def test_is_safe() -> None:
    assert json_minify.RISK is Risk.SAFE


def test_minify_keeps_spaces_inside_strings() -> None:
    text = '{ "a b": "x  y", "q": "say \\"hi \\" ok" }'
    assert json_minify.minify(text) == '{"a b":"x  y","q":"say \\"hi \\" ok"}'


def test_minifies_inline_block(apply_rule) -> None:
    text = f"Use this data:\n{PRETTY}\nThanks"
    result = apply_rule(json_minify, text)
    assert result == 'Use this data:\n{"name":"Ada Lovelace","tags":["math","code"]}\nThanks'


def test_minifies_fenced_block(apply_rule) -> None:
    text = f"```json\n{PRETTY}\n```"
    assert apply_rule(json_minify, text) == (
        '```json\n{"name":"Ada Lovelace","tags":["math","code"]}\n```'
    )


def test_minifies_fenced_block_after_other_text(apply_rule) -> None:
    text = f"Prices:\n\n```json\n{PRETTY}\n```\nEnd"
    assert apply_rule(json_minify, text) == (
        'Prices:\n\n```json\n{"name":"Ada Lovelace","tags":["math","code"]}\n```\nEnd'
    )


def test_data_is_unchanged(apply_rule) -> None:
    result = apply_rule(json_minify, PRETTY)
    assert json.loads(result) == json.loads(PRETTY)


def test_number_formats_and_duplicate_keys_are_preserved(apply_rule) -> None:
    text = '{\n  "price": 1.50,\n  "big": 1e5,\n  "k": 1,\n  "k": 2\n}'
    assert apply_rule(json_minify, text) == '{"price":1.50,"big":1e5,"k":1,"k":2}'


def test_ignores_invalid_json_and_prose(apply_rule) -> None:
    for text in [
        "{ this is not json }",
        "[note] remember this",
        '{"a": 1} and then some prose',
        "```json\n{ broken: true }\n```",
    ]:
        assert apply_rule(json_minify, text) == text


def test_already_minified_has_no_suggestion() -> None:
    assert json_minify.find('{"a":1}') == []


def test_reports_line_number() -> None:
    [suggestion] = json_minify.find(f"line one\nline two\n{PRETTY}")
    assert suggestion.line == 3
