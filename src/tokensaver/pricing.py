"""Model prices and metadata, loaded from data/prices.json."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

DEFAULT_PRICES_PATH = Path(__file__).parent / "data" / "prices.json"
TOKENS_PER_PRICE_UNIT = 1_000_000


class PriceDataError(ValueError):
    """prices.json is missing a field or has an invalid value."""


class UnknownModelError(KeyError):
    """The requested model is not in prices.json."""

    def __init__(self, model: str, suggestions: list[str]) -> None:
        self.model = model
        self.suggestions = suggestions
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"Unknown model '{model}'.{hint}")

    def __str__(self) -> str:
        return self.args[0]


@dataclass(frozen=True)
class ModelInfo:
    name: str
    provider: str
    input_per_1m: float
    output_per_1m: float
    tokenizer: str
    exact: bool
    estimate_factor: float
    source_url: str
    notes: str = ""


@dataclass(frozen=True)
class PriceTable:
    last_updated: date
    models: dict[str, ModelInfo]

    def get(self, name: str) -> ModelInfo:
        try:
            return self.models[name]
        except KeyError:
            close = difflib.get_close_matches(name, self.models, n=3, cutoff=0.5)
            raise UnknownModelError(name, close) from None


def _require(entry: dict, field: str, model: str) -> object:
    if field not in entry:
        raise PriceDataError(f"Model '{model}' is missing '{field}'.")
    return entry[field]


def _parse_model(name: str, entry: dict) -> ModelInfo:
    input_price = float(_require(entry, "input_per_1m", name))
    output_price = float(_require(entry, "output_per_1m", name))
    if input_price < 0 or output_price < 0:
        raise PriceDataError(f"Model '{name}' has a negative price.")

    exact = bool(_require(entry, "exact", name))
    factor = 1.0 if exact else float(_require(entry, "estimate_factor", name))
    if factor <= 0:
        raise PriceDataError(f"Model '{name}' needs a positive estimate_factor.")

    return ModelInfo(
        name=name,
        provider=str(_require(entry, "provider", name)),
        input_per_1m=input_price,
        output_per_1m=output_price,
        tokenizer=str(_require(entry, "tokenizer", name)),
        exact=exact,
        estimate_factor=factor,
        source_url=str(_require(entry, "source_url", name)),
        notes=str(entry.get("notes", "")),
    )


def parse_prices(raw: dict) -> PriceTable:
    """Validate and convert the raw JSON structure into a PriceTable."""
    try:
        last_updated = date.fromisoformat(str(raw["last_updated"]))
    except KeyError:
        raise PriceDataError("prices.json is missing 'last_updated'.") from None
    except ValueError:
        raise PriceDataError("'last_updated' must be a date like 2026-10-26.") from None

    models = raw.get("models")
    if not isinstance(models, dict) or not models:
        raise PriceDataError("prices.json needs a non-empty 'models' object.")

    parsed = {name: _parse_model(name, entry) for name, entry in models.items()}
    return PriceTable(last_updated=last_updated, models=parsed)


def load_prices(path: Path | None = None) -> PriceTable:
    """Load a price table. Without a path, the bundled prices.json is used (cached)."""
    if path is None:
        return _load_default()
    return parse_prices(json.loads(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def _load_default() -> PriceTable:
    return parse_prices(json.loads(DEFAULT_PRICES_PATH.read_text(encoding="utf-8")))


def input_cost(tokens: int, model: ModelInfo) -> float:
    """Dollar cost of sending `tokens` input tokens to `model`."""
    return tokens * model.input_per_1m / TOKENS_PER_PRICE_UNIT
