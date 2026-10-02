"""ETF signal model tests (Phase 1). No network calls."""

import sys

sys.path.insert(0, "src")

import pytest
from pydantic import ValidationError

from hollow_green.etf_signals import MODEL_VERSION, TRACKED_ETFS, Signal, is_tracked


def make_signal(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "date": "2026-10-02",
        "ticker": "VOO",
        "direction": "up",
        "confidence": 0.75,
        "headlines_used": ["Market rallies on jobs data"],
        "model_version": MODEL_VERSION,
    }
    base.update(overrides)
    return base


def test_tracked_etfs_lists_five():
    assert TRACKED_ETFS == ("VOO", "SPY", "QQQ", "XLK", "XLE")


def test_is_tracked():
    assert is_tracked("VOO")
    assert is_tracked("XLE")
    assert not is_tracked("AAPL")
    assert not is_tracked("voo")


def test_valid_signal_parses():
    signal = Signal.model_validate(make_signal())
    assert signal.ticker == "VOO"
    assert signal.direction == "up"
    assert signal.confidence == 0.75
    assert signal.outcome is None
    assert signal.model_version == MODEL_VERSION
    assert str(signal.date) == "2026-10-02"


def test_valid_signal_with_outcome():
    signal = Signal.model_validate(make_signal(outcome="down"))
    assert signal.outcome == "down"


def test_all_tracked_tickers_accepted():
    for ticker in TRACKED_ETFS:
        signal = Signal.model_validate(make_signal(ticker=ticker))
        assert signal.ticker == ticker


def test_rejects_unknown_ticker():
    with pytest.raises(ValidationError):
        Signal.model_validate(make_signal(ticker="AAPL"))


def test_rejects_bad_direction():
    with pytest.raises(ValidationError):
        Signal.model_validate(make_signal(direction="sideways"))
    with pytest.raises(ValidationError):
        Signal.model_validate(make_signal(outcome="flat"))


def test_confidence_bounds():
    assert Signal.model_validate(make_signal(confidence=0.0)).confidence == 0.0
    assert Signal.model_validate(make_signal(confidence=1.0)).confidence == 1.0
    with pytest.raises(ValidationError):
        Signal.model_validate(make_signal(confidence=-0.1))
    with pytest.raises(ValidationError):
        Signal.model_validate(make_signal(confidence=1.1))


def test_rejects_empty_model_version():
    with pytest.raises(ValidationError):
        Signal.model_validate(make_signal(model_version=""))


def test_headlines_default_to_empty_list():
    payload = make_signal()
    del payload["headlines_used"]
    assert Signal.model_validate(payload).headlines_used == []
