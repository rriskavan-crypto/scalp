"""Broker qatlami: umumiy interfeys, simulyator va MetaTrader 5.

`MT5Broker` faqat Windows'da ishlaydi, lekin import qilinishi xavfsiz —
xato faqat `connect()` chaqirilganda va tushunarli matn bilan chiqadi.
"""

from .base import (
    AccountState, Broker, BrokerPosition, OrderResult, PendingOrder, Quote,
    SymbolSpec,
)
from .paper import PaperBroker

__all__ = [
    "Broker", "SymbolSpec", "AccountState", "Quote", "BrokerPosition",
    "PendingOrder", "OrderResult", "PaperBroker", "MT5Broker", "MT5Credentials",
]


def __getattr__(name: str):
    """MT5 sinflari faqat so'ralganda yuklanadi."""
    if name in ("MT5Broker", "MT5Credentials"):
        from . import mt5broker
        return getattr(mt5broker, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
