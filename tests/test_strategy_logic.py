from collections import deque

from config import LONG_WINDOW, SHORT_WINDOW
from strategy import StrategyEngine

TEST_SYMBOLS = ["AAA", "BBB"]


class DummyPriceBook:
    def snapshot(self):
        return {symbol: 100.0 for symbol in TEST_SYMBOLS}


class DummySocket:
    def __init__(self):
        self.payloads = []

    def sendall(self, data: bytes):
        self.payloads.append(data)


def build_engine():
    return StrategyEngine(
        price_book=DummyPriceBook(),
        lock=None,
        host="127.0.0.1",
        news_port=6001,
        order_port=6002,
        symbols=TEST_SYMBOLS,
    )


def test_price_signal_buy():
    engine = build_engine()
    history = deque(maxlen=LONG_WINDOW)
    base = 100.0
    for i in range(LONG_WINDOW):
        history.append(base + i * 0.1)
    assert engine._price_signal(history) == "BUY"


def test_price_signal_sell():
    engine = build_engine()
    history = deque(maxlen=LONG_WINDOW)
    for i in range(LONG_WINDOW):
        history.append(100.0 - i * 0.1)
    assert engine._price_signal(history) == "SELL"


def test_maybe_trade_requires_matching_signals():
    engine = build_engine()
    symbol = TEST_SYMBOLS[0]
    engine.latest_sentiment = 80  # BUY news signal
    engine.order_socket = DummySocket()
    engine.positions[symbol] = None
    engine._maybe_trade(symbol, 123.45, price_signal="BUY", price_timestamp=0.0)
    assert engine.positions[symbol] == "LONG"
    assert engine.order_socket.payloads, "Order should be sent when signals match"


def test_maybe_trade_no_trade_on_mismatch():
    engine = build_engine()
    symbol = TEST_SYMBOLS[0]
    engine.latest_sentiment = 20  # SELL news signal
    engine.order_socket = DummySocket()
    engine.positions[symbol] = None
    engine._maybe_trade(symbol, 120.0, price_signal="BUY", price_timestamp=0.0)
    assert engine.positions[symbol] is None
    assert not engine.order_socket.payloads
