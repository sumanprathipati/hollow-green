"""ETF signal tracker (Phase 1): typed config and signal models only.

No network calls, no secrets, no scoring. This module sits alongside the
existing Hollow Green engine without changing it.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

TRACKED_ETFS: tuple[str, ...] = ("VOO", "SPY", "QQQ", "XLK", "XLE")

Ticker = Literal["VOO", "SPY", "QQQ", "XLK", "XLE"]
Direction = Literal["up", "down"]

MODEL_VERSION = "phase1-0.1"


class Signal(BaseModel):
    date: date
    ticker: Ticker
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)
    headlines_used: list[str] = Field(default_factory=list)
    outcome: Direction | None = None
    model_version: str = Field(min_length=1)


def is_tracked(ticker: str) -> bool:
    return ticker in TRACKED_ETFS
