"""USD per 1M tokens (Anthropic first-party list prices, cached 2026-11-03). Unknown model -> Opus 5.5 price."""
PRICES = {
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.10},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cache_read": 0.01},
    "claude-fable-5-2": {"in": 8.00, "out": 40.00, "cache_read": 0.20},
}


def cost(model: str, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_write: int = 0) -> float:
    p = PRICES.get(model, PRICES["claude-opus-5-5"])
    usd = (input_tokens * p["in"] + output_tokens * p["out"] + cache_read * p["cache_read"]
           + cache_write * p["in"] * 1.25) / 1_000_000
    return round(usd, 6)
