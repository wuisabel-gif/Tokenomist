"""Tests for token estimation and the pricing/latency models."""

from __future__ import annotations

from agenttracelab.pricing import DEFAULT_PRICES, PriceBook
from agenttracelab.tokens import estimate_tokens


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0
    assert estimate_tokens(None) == 0


def test_estimate_tokens_nonzero():
    assert estimate_tokens("hello world") >= 1
    # Longer text yields more tokens.
    assert estimate_tokens("a" * 400) > estimate_tokens("a" * 40)


def test_pricebook_resolve_exact_and_fuzzy():
    book = PriceBook()
    assert book.resolve("claude-opus") is DEFAULT_PRICES["claude-opus"]
    # Fuzzy substring match.
    assert book.resolve("claude-opus-4-8") is DEFAULT_PRICES["claude-opus"]


def test_pricebook_unknown_uses_generic():
    book = PriceBook()
    price = book.resolve("totally-unknown-model")
    assert price.input_per_mtok > 0


def test_cost_scales_with_output():
    book = PriceBook()
    cheap = book.cost_usd("gpt-4o", 1000, 0)
    pricier = book.cost_usd("gpt-4o", 1000, 1000)
    assert pricier > cheap


def test_latency_grows_with_output():
    book = PriceBook()
    assert book.latency_ms("gpt-4o", 1000) > book.latency_ms("gpt-4o", 10)


def test_custom_pricebook_overrides():
    from agenttracelab.pricing import ModelPrice

    book = PriceBook({"mymodel": ModelPrice(1.0, 2.0, 50.0)})
    assert book.cost_usd("mymodel", 1_000_000, 0) == 1.0
