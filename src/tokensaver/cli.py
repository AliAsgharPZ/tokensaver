"""Command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from tokensaver import __version__
from tokensaver.counter import count_tokens
from tokensaver.inputs import PromptInput, resolve_input
from tokensaver.optimizer import RULE_NAMES, optimize, resolve_selection
from tokensaver.output import render_compare, render_count, render_models, render_optimize
from tokensaver.pricing import (
    ModelInfo,
    PriceDataError,
    PriceTable,
    UnknownModelError,
    load_prices,
)

DEFAULT_MODEL = "gpt-4o"

app = typer.Typer(
    help="Count tokens, compare model costs and get concrete savings for your prompts. "
    "Everything runs offline; your prompt never leaves your machine.",
    no_args_is_help=True,
    add_completion=False,
)

InputArg = Annotated[
    str,
    typer.Argument(help="A file path, '-' for stdin, or the prompt text itself.", metavar="INPUT"),
]
ModelOpt = Annotated[
    str, typer.Option("--model", "-m", help="Model to price against (see 'tokensaver models').")
]
PricesOpt = Annotated[
    Path | None,
    typer.Option(help="Use a custom prices.json instead of the bundled one.", dir_okay=False),
]


def _console() -> Console:
    return Console(highlight=False)


def _fail(message: str) -> typer.Exit:
    Console(stderr=True, highlight=False).print(f"[red]Error:[/red] {message}", markup=True)
    return typer.Exit(code=2)


def _load_table(prices: Path | None) -> PriceTable:
    try:
        return load_prices(prices)
    except FileNotFoundError:
        raise _fail(f"Prices file not found: {prices}") from None
    except (PriceDataError, ValueError) as error:
        raise _fail(f"Invalid prices file: {error}") from None


def _get_model(table: PriceTable, name: str) -> ModelInfo:
    try:
        return table.get(name)
    except UnknownModelError as error:
        raise _fail(f"{error} Run 'tokensaver models' to list them.") from None


def _read(value: str) -> PromptInput:
    try:
        return resolve_input(value)
    except FileNotFoundError as error:
        raise _fail(str(error)) from None
    except UnicodeDecodeError:
        raise _fail(f"{value} is not UTF-8 text.") from None


@app.callback()
def main() -> None:
    """Count tokens, compare model costs and get concrete savings for your prompts."""
    # Never crash on characters a legacy Windows code page cannot show.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


@app.command()
def count(input: InputArg, model: ModelOpt = DEFAULT_MODEL, prices: PricesOpt = None) -> None:
    """Show the token count and input cost for one model."""
    table = _load_table(prices)
    info = _get_model(table, model)
    prompt = _read(input)
    render_count(_console(), count_tokens(prompt.text, info), info, table, prompt.source)


@app.command()
def compare(
    input: InputArg,
    models: Annotated[
        str | None,
        typer.Option(help="Comma-separated models to compare (default: all)."),
    ] = None,
    prices: PricesOpt = None,
) -> None:
    """Compare tokens and input cost across models, cheapest first."""
    table = _load_table(prices)
    names = [n.strip() for n in models.split(",") if n.strip()] if models else list(table.models)
    infos = [_get_model(table, name) for name in names]
    prompt = _read(input)
    rows = [(info, count_tokens(prompt.text, info)) for info in infos]
    render_compare(_console(), rows, table, prompt.source)


@app.command(name="optimize")
def optimize_command(
    input: InputArg,
    model: ModelOpt = DEFAULT_MODEL,
    apply: Annotated[
        str,
        typer.Option(
            help="Rules to apply: 'safe' (default), 'all', 'none' or a comma list of: "
            + ", ".join(RULE_NAMES)
        ),
    ] = "safe",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Save the optimized prompt to this file.", dir_okay=False
        ),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite --output if it already exists.")
    ] = False,
    diff: Annotated[
        bool, typer.Option("--diff/--no-diff", help="Show the before/after diff.")
    ] = True,
    prices: PricesOpt = None,
) -> None:
    """Suggest concrete changes, with the tokens and dollars each one saves."""
    table = _load_table(prices)
    info = _get_model(table, model)
    try:
        selected = resolve_selection(apply)
    except ValueError as error:
        raise _fail(str(error)) from None
    prompt = _read(input)

    if output is not None:
        _check_output(output, prompt, force)

    result = optimize(prompt.text, info, selected)
    extra_if_all = 0
    if any(not f.applied and not f.suggestion.flag_only for f in result.findings):
        everything = optimize(prompt.text, info, resolve_selection("all"))
        extra_if_all = max(result.tokens_after - everything.tokens_after, 0)
    console = _console()
    render_optimize(
        console, result, table, prompt.source, show_diff=diff, extra_if_all=extra_if_all
    )

    if output is not None:
        output.write_text(result.optimized, encoding="utf-8")
        console.print(f"Saved optimized prompt to {output}", markup=False)


def _check_output(output: Path, prompt: PromptInput, force: bool) -> None:
    """Never overwrite the input file; only overwrite other files with --force."""
    if prompt.path is not None and output.exists() and output.resolve() == prompt.path.resolve():
        raise _fail("--output must be a different file; the original is never overwritten.")
    if output.exists() and not force:
        raise _fail(f"{output} already exists. Use --force to overwrite it.")


@app.command()
def models(prices: PricesOpt = None) -> None:
    """List supported models and their prices."""
    render_models(_console(), _load_table(prices))


@app.command()
def version() -> None:
    """Show the installed version."""
    typer.echo(__version__)
