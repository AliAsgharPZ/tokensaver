# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.1] - 2026-10-26

Fixes the PyPI project page (images and links); no change to how tokensaver works.

### Added
- Demo image and PyPI badge in the README; README links are absolute so they work on PyPI.
- Issue forms, pull request template, code of conduct and security policy.
- PyPI publishing workflow (trusted publishing, no stored token).

### Changed
- CI uses `actions/checkout@v7` and `actions/setup-python@v7`.

## [0.1.0] - 2026-10-26

First release, published on PyPI as `prompt-tokensaver` (command: `tokensaver`).

### Added
- Project setup: `pyproject.toml`, `src/` layout, ruff, pytest.
- Offline token counting with bundled tiktoken encodings (`o200k_base`, `cl100k_base`).
- `prices.json` with 20 OpenAI, Anthropic and Google models, source URLs and `last_updated`.
- Optimizer with six rules: `json` and `whitespace` (safe), `duplicates`,
  `repeated-instructions`, `filler` and `long-examples` (review; long-examples only flags).
- CLI: `count`, `compare`, `optimize` (`--apply`, `--output`, `--force`, `--no-diff`),
  `models`, `version`; input from a file, stdin (`-`) or literal text; `--prices` override.
- Line numbers in suggestions always refer to the original file.
- Few-shot examples are protected from wording rules.
- `examples/messy_prompt.txt`, README, CONTRIBUTING and CI (ruff + pytest on Windows,
  macOS and Linux, Python 3.10 and 3.13).
