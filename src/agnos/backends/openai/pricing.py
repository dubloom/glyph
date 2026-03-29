"""OpenAI usage-cost estimation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class OpenAIModelPricing:
    """Per-1M-token pricing for one model family."""

    input_usd_per_million: float
    output_usd_per_million: float
    cached_input_usd_per_million: float | None = None


# Standard OpenAI pricing (USD / 1M tokens).
# Keep keys as model-family prefixes; longest prefix wins.
_OPENAI_PRICING_BY_PREFIX: dict[str, OpenAIModelPricing] = {
    "gpt-4.1-nano": OpenAIModelPricing(0.10, 0.40, 0.025),
    "gpt-4.1-mini": OpenAIModelPricing(0.40, 1.60, 0.10),
    "gpt-4.1": OpenAIModelPricing(2.00, 8.00, 0.50),
    "o4-mini": OpenAIModelPricing(1.10, 4.40, 0.275),
    "o3": OpenAIModelPricing(2.00, 8.00, 0.50),
}


def get_openai_model_pricing(model: str) -> OpenAIModelPricing | None:
    """Return pricing for a model id, using prefix matching."""
    normalized = model.strip().lower()
    if not normalized:
        return None
    for prefix in sorted(_OPENAI_PRICING_BY_PREFIX, key=len, reverse=True):
        if normalized.startswith(prefix):
            return _OPENAI_PRICING_BY_PREFIX[prefix]
    return None


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _cached_input_tokens(usage: dict[str, Any] | None) -> int:
    if not usage:
        return 0
    details = usage.get("input_tokens_details")
    if isinstance(details, list) and details:
        details = details[0]
    if not isinstance(details, dict):
        return 0
    return _as_int(details.get("cached_tokens"), default=0)


def estimate_openai_total_cost_usd(
    *,
    model: str,
    usage: dict[str, Any] | None,
) -> float | None:
    """Estimate total request cost (USD) from OpenAI token usage.

    Returns ``None`` if the model has no configured pricing table.
    """
    pricing = get_openai_model_pricing(model)
    if pricing is None:
        return None

    input_tokens = _as_int((usage or {}).get("input_tokens"), default=0)
    output_tokens = _as_int((usage or {}).get("output_tokens"), default=0)
    cached_tokens = max(0, _cached_input_tokens(usage))
    non_cached_input_tokens = max(0, input_tokens - cached_tokens)

    input_cost_usd = (non_cached_input_tokens / _TOKENS_PER_MILLION) * pricing.input_usd_per_million
    output_cost_usd = (output_tokens / _TOKENS_PER_MILLION) * pricing.output_usd_per_million

    if pricing.cached_input_usd_per_million is not None:
        cached_input_cost_usd = (
            (cached_tokens / _TOKENS_PER_MILLION) * pricing.cached_input_usd_per_million
        )
    else:
        cached_input_cost_usd = (cached_tokens / _TOKENS_PER_MILLION) * pricing.input_usd_per_million

    return input_cost_usd + cached_input_cost_usd + output_cost_usd
