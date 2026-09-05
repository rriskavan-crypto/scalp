"""Strategiya reyestri."""

from __future__ import annotations

from typing import Any

from .base import Strategy
from .momentum_pullback import MomentumPullback

REGISTRY: dict[str, type[Strategy]] = {
    MomentumPullback.name: MomentumPullback,
}


def get_strategy(name: str, params: dict[str, Any] | None = None) -> Strategy:
    if name not in REGISTRY:
        raise KeyError(f"Noma'lum strategiya '{name}'. Mavjud: {sorted(REGISTRY)}")
    return REGISTRY[name](params)


def available() -> list[str]:
    return sorted(REGISTRY)


__all__ = ["Strategy", "MomentumPullback", "REGISTRY", "get_strategy", "available"]
