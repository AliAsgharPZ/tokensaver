# Contributing to tokensaver

Thanks for helping make AI cheaper to use! This guide gets you from clone to green tests
in about five minutes.

## Setup

**Windows (PowerShell)**

```powershell
git clone https://github.com/behrouzbk/tokensaver.git
cd tokensaver
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

If PowerShell says running scripts is disabled, allow scripts for your user only, then
try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**macOS / Linux**

```bash
git clone https://github.com/behrouzbk/tokensaver.git
cd tokensaver
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Check your work

```bash
ruff check .
ruff format --check .
pytest
```

All three must pass. CI runs them on Windows, macOS and Linux.

## Ground rules

- **Offline only.** No network calls, no telemetry. A user's prompt must never leave
  their machine.
- **Never present an estimate as exact.** If a count is not exact, it must be labelled.
- **Never change meaning silently.** Rules that might change meaning are `Risk.REVIEW`.
- **No new runtime dependencies** without discussing it in an issue first.
- Use `pathlib` for paths and `encoding="utf-8"` for every file read and write.
- Small functions, type hints, and a test for every behaviour.

## Adding an optimizer rule

1. Create `src/tokensaver/optimizer/my_rule.py` with:
   - `NAME = "my-rule"`: the name users pass to `--apply`
   - `RISK = Risk.SAFE` or `Risk.REVIEW` (safe means meaning cannot change)
   - `def find(text: str) -> list[Suggestion]`
2. Each `Suggestion` holds non-overlapping `Edit`s (start, end, replacement) on `text`,
   or only a `span` if it just flags something. Skip text inside
   `protected_spans(text)` (code blocks and few-shot examples) if your rule rewrites
   wording.
3. Register the module in `RULES` in `src/tokensaver/optimizer/__init__.py`.
4. Add `tests/optimizer/test_my_rule.py`. The `apply_rule` fixture applies all edits a
   rule suggests, so most tests are one line: `assert apply_rule(my_rule, before) == after`.
5. Add the rule to the table in `README.md` and a line in `CHANGELOG.md`.

You do not need to calculate savings: the engine measures tokens before and after each
suggestion on the user's model.

## Updating prices

Prices live in `src/tokensaver/data/prices.json`.

1. Change the numbers (USD per 1M tokens, standard tier).
2. Keep `source_url` pointing at the provider's official pricing page.
3. Update `last_updated` to the date you checked.
4. Set `"exact": true` only if `tiktoken.encoding_name_for_model()` returns that model's
   `tokenizer`. A test enforces this. Every other model needs an `estimate_factor`.
5. Update the models table in `README.md`.

## Pull requests

- One topic per pull request, with a short description of the why.
- Include tests and keep `ruff` and `pytest` green.
- Add a line under `[Unreleased]` in `CHANGELOG.md`.

## Releasing (maintainer)

PyPI publishing uses [trusted publishing](https://docs.pypi.org/trusted-publishers/), so
no API token is stored.

1. One time only: on pypi.org, go to *Your account → Publishing → Add a pending
   publisher* and enter: project `prompt-tokensaver`, owner `behrouzbk`, repository
   `tokensaver`, workflow `publish.yml`, environment `pypi`.
2. Bump `version` in `pyproject.toml` and `src/tokensaver/__init__.py`, and move the
   `[Unreleased]` notes in `CHANGELOG.md` under the new version.
3. Commit, then create a GitHub Release with a `vX.Y.Z` tag. The *Publish to PyPI*
   workflow builds and uploads the package.

## Reporting bugs

Open an issue with the command you ran, what you expected and what happened. If you
share a prompt, remove anything private first.
