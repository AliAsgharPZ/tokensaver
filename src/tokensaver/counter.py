"""Token counting. Exact for OpenAI models via tiktoken, labelled estimates otherwise.

The tiktoken encoding files ship inside the package, so counting never touches the
network. The definitions below mirror tiktoken_ext.openai_public; tests compare the
results against counts produced by the official tiktoken loader.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import tiktoken

from tokensaver.pricing import ModelInfo

ENCODINGS_DIR = Path(__file__).parent / "data" / "encodings"

_O200K_PATTERN = "|".join(
    [
        r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
        r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
        r"""\p{N}{1,3}""",
        r""" ?[^\s\p{L}\p{N}]+[\r\n/]*""",
        r"""\s*[\r\n]+""",
        r"""\s+(?!\S)""",
        r"""\s+""",
    ]
)
_CL100K_PATTERN = r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++|\p{N}{1,3}+| ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$|\s*[\r\n]|\s+(?!\S)|\s"""  # noqa: E501

_ENCODINGS = {
    "o200k_base": {
        "sha256": "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d",
        "pat_str": _O200K_PATTERN,
        "special_tokens": {"<|endoftext|>": 199999, "<|endofprompt|>": 200018},
    },
    "cl100k_base": {
        "sha256": "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7",
        "pat_str": _CL100K_PATTERN,
        "special_tokens": {
            "<|endoftext|>": 100257,
            "<|fim_prefix|>": 100258,
            "<|fim_middle|>": 100259,
            "<|fim_suffix|>": 100260,
            "<|endofprompt|>": 100276,
        },
    },
}


@dataclass(frozen=True)
class TokenCount:
    model: str
    tokens: int
    exact: bool


def _load_ranks(name: str, expected_sha256: str) -> dict[bytes, int]:
    data = (ENCODINGS_DIR / f"{name}.tiktoken").read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise RuntimeError(f"Bundled encoding file {name}.tiktoken is corrupted.")
    ranks = {}
    for line in data.splitlines():
        if line:
            token, rank = line.split()
            ranks[base64.b64decode(token)] = int(rank)
    return ranks


@cache
def get_encoding(name: str) -> tiktoken.Encoding:
    """Build a tiktoken Encoding from the bundled files (no network access)."""
    if name not in _ENCODINGS:
        raise ValueError(f"Unsupported tokenizer '{name}'. Supported: {', '.join(_ENCODINGS)}")
    spec = _ENCODINGS[name]
    return tiktoken.Encoding(
        name=name,
        pat_str=spec["pat_str"],
        mergeable_ranks=_load_ranks(name, spec["sha256"]),
        special_tokens=spec["special_tokens"],
    )


def count_raw(text: str, tokenizer: str) -> int:
    """Token count for a tokenizer. Special-token text is counted as plain text."""
    return len(get_encoding(tokenizer).encode_ordinary(text))


def count_tokens(text: str, model: ModelInfo) -> TokenCount:
    """Count tokens for a model; non-exact models get a scaled estimate."""
    raw = count_raw(text, model.tokenizer)
    tokens = raw if model.exact else round(raw * model.estimate_factor)
    return TokenCount(model=model.name, tokens=tokens, exact=model.exact)
