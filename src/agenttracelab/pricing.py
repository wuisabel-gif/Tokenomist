"""Cost and latency models.

Prices are expressed in USD per million tokens and split into input
(prompt) and output (completion) rates, matching how the major providers
bill. The numbers here are approximate public list prices and are meant for
*relative* comparison between agents, not for billing. Override them by
passing a custom :class:`PriceBook` to the analyzer.

Latency is estimated from output tokens using a simple throughput model
(tokens-per-second) plus a fixed per-turn overhead, which is enough to rank
agents by responsiveness when raw timestamps are missing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    """Per-million-token prices and a rough output throughput."""

    input_per_mtok: float
    output_per_mtok: float
    output_tokens_per_sec: float = 60.0


# Approximate public list prices (USD / 1M tokens). Configurable, not authoritative.
DEFAULT_PRICES: dict[str, ModelPrice] = {
    # Anthropic
    "claude-opus": ModelPrice(15.0, 75.0, 45.0),
    "claude-sonnet": ModelPrice(3.0, 15.0, 65.0),
    "claude-haiku": ModelPrice(0.80, 4.0, 120.0),
    # OpenAI
    "gpt-4o": ModelPrice(2.5, 10.0, 80.0),
    "gpt-4o-mini": ModelPrice(0.15, 0.60, 130.0),
    "o3": ModelPrice(10.0, 40.0, 40.0),
    # Google
    "gemini-1.5-pro": ModelPrice(1.25, 5.0, 70.0),
    "gemini-1.5-flash": ModelPrice(0.075, 0.30, 150.0),
    "gemini-2.0-flash": ModelPrice(0.10, 0.40, 160.0),
}

# Fallback used when a conversation does not name a known model.
_GENERIC_PRICE = ModelPrice(2.0, 8.0, 70.0)

# Fixed per-turn overhead added to the throughput-derived latency estimate.
_TURN_OVERHEAD_MS = 350.0


class PriceBook:
    """Lookup of model name -> :class:`ModelPrice` with fuzzy matching."""

    def __init__(self, prices: dict[str, ModelPrice] | None = None) -> None:
        self._prices = dict(DEFAULT_PRICES if prices is None else prices)

    def resolve(self, model: str | None) -> ModelPrice:
        """Return the price for ``model``, matching on known name fragments."""

        if not model:
            return _GENERIC_PRICE
        key = model.lower()
        if key in self._prices:
            return self._prices[key]
        # Substring match so "claude-opus-4-8" maps to the "claude-opus" entry.
        for name, price in self._prices.items():
            if name in key or key in name:
                return price
        return _GENERIC_PRICE

    def cost_usd(self, model: str | None, input_tokens: int, output_tokens: int) -> float:
        price = self.resolve(model)
        return (
            input_tokens / 1_000_000 * price.input_per_mtok
            + output_tokens / 1_000_000 * price.output_per_mtok
        )

    def latency_ms(self, model: str | None, output_tokens: int) -> float:
        """Estimate generation latency from output token count."""

        price = self.resolve(model)
        tps = price.output_tokens_per_sec or 60.0
        return _TURN_OVERHEAD_MS + (output_tokens / tps) * 1000.0
