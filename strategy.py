from __future__ import annotations

import json
import math
import socket
import time
from collections import deque
from multiprocessing.synchronize import Lock
from typing import Deque, Dict, Optional

from config import (
    BEARISH_THRESHOLD,
    BULLISH_THRESHOLD,
    HOST,
    LONG_WINDOW,
    MAX_PRICE_HISTORY,
    MESSAGE_DELIMITER,
    NEWS_FEED_PORT,
    ORDER_MANAGER_PORT,
    ORDER_QUANTITY,
    SHORT_WINDOW,
    SYMBOLS,
    SHARED_MEMORY_NAME,
)
from shared_memory_utils import SharedPriceBook


def run_strategy(
    lock: Optional[Lock] = None,
    host: str = HOST,
    news_port: int = NEWS_FEED_PORT,
    order_port: int = ORDER_MANAGER_PORT,
    symbols=None,
    shared_name: str = SHARED_MEMORY_NAME,
) -> None:
    symbols = list(symbols or SYMBOLS)
    price_book = _attach_price_book(symbols, shared_name)
    engine = StrategyEngine(
        price_book=price_book,
        lock=lock,
        host=host,
        news_port=news_port,
        order_port=order_port,
        symbols=symbols,
    )
    try:
        engine.run()
    finally:
        price_book.close()


def _attach_price_book(
    symbols, shared_name: str, retry_delay: float = 0.5
) -> SharedPriceBook:
    while True:
        try:
            return SharedPriceBook(symbols, name=shared_name)
        except FileNotFoundError:
            print("[Strategy] Waiting for shared memory...")
            time.sleep(retry_delay)


class StrategyEngine:
    def __init__(
        self,
        price_book: SharedPriceBook,
        lock: Optional[Lock],
        host: str,
        news_port: int,
        order_port: int,
        symbols,
    ):
        self.price_book = price_book
        self.lock = lock
        self.host = host
        self.news_port = news_port
        self.order_port = order_port
        self.symbols = list(symbols)
        self.price_history: Dict[str, Deque[float]] = {
            symbol: deque(maxlen=MAX_PRICE_HISTORY) for symbol in self.symbols
        }
        self.positions: Dict[str, Optional[str]] = {symbol: None for symbol in self.symbols}
        self.latest_sentiment: Optional[int] = None
        self.news_socket: Optional[socket.socket] = None
        self.news_buffer = b""
        self.order_socket: Optional[socket.socket] = None

    def run(self) -> None:
        print("[Strategy] Started.")
        while True:
            try:
                self._ensure_connections()
                self._consume_news()
                self._process_prices()
                time.sleep(0.2)
            except KeyboardInterrupt:
                break

    def _ensure_connections(self) -> None:
        if self.news_socket is None:
            self.news_socket = self._connect(self.news_port)
            if self.news_socket:
                self.news_socket.setblocking(False)
        if self.order_socket is None:
            self.order_socket = self._connect(self.order_port)

    def _connect(self, port: int) -> Optional[socket.socket]:
        try:
            sock = socket.create_connection((self.host, port))
            print(f"[Strategy] Connected to port {port}.")
            return sock
        except OSError:
            print(f"[Strategy] Unable to reach port {port}, retrying shortly.")
            time.sleep(1)
            return None

    def _consume_news(self) -> None:
        if not self.news_socket:
            return
        while True:
            try:
                chunk = self.news_socket.recv(1024)
                if not chunk:
                    print("[Strategy] News stream closed, reconnecting.")
                    self.news_socket.close()
                    self.news_socket = None
                    break
                self.news_buffer += chunk
                while True:
                    idx = self.news_buffer.find(MESSAGE_DELIMITER)
                    if idx == -1:
                        break
                    token = self.news_buffer[:idx]
                    self.news_buffer = self.news_buffer[idx + len(MESSAGE_DELIMITER) :]
                    if token:
                        self._handle_sentiment(token)
            except BlockingIOError:
                break
            except OSError:
                self.news_socket = None
                break

    def _handle_sentiment(self, token: bytes) -> None:
        try:
            value = int(token.decode())
            self.latest_sentiment = value
        except ValueError:
            print(f"[Strategy] Invalid sentiment chunk: {token!r}")

    def _process_prices(self) -> None:
        if self.lock:
            with self.lock:
                snapshot = self.price_book.snapshot()
        else:
            snapshot = self.price_book.snapshot()

        for symbol, price in snapshot.items():
            if math.isnan(price):
                continue
            history = self.price_history[symbol]
            if not history or history[-1] != price:
                history.append(price)
                price_signal = self._price_signal(history)
                price_timestamp = time.time()
                self._maybe_trade(symbol, price, price_signal, price_timestamp)

    def _price_signal(self, history: Deque[float]) -> Optional[str]:
        if len(history) < LONG_WINDOW:
            return None
        short_avg = sum(list(history)[-SHORT_WINDOW:]) / SHORT_WINDOW
        long_avg = sum(history) / len(history)
        if short_avg > long_avg:
            return "BUY"
        if short_avg < long_avg:
            return "SELL"
        return None

    def _news_signal(self) -> Optional[str]:
        if self.latest_sentiment is None:
            return None
        if self.latest_sentiment > BULLISH_THRESHOLD:
            return "BUY"
        if self.latest_sentiment < BEARISH_THRESHOLD:
            return "SELL"
        return None

    def _maybe_trade(
        self,
        symbol: str,
        price: float,
        price_signal: Optional[str],
        price_timestamp: float,
    ) -> None:
        news_signal = self._news_signal()
        if not price_signal or not news_signal:
            return
        if price_signal != news_signal:
            return
        desired_position = "LONG" if price_signal == "BUY" else "SHORT"
        current_position = self.positions[symbol]
        if current_position == desired_position:
            return
        self.positions[symbol] = desired_position
        self._send_order(symbol, price_signal, price, price_timestamp)

    def _send_order(self, symbol: str, side: str, price: float, price_timestamp: float) -> None:
        if not self.order_socket:
            return
        order = {
            "symbol": symbol,
            "side": side,
            "quantity": ORDER_QUANTITY,
            "price": round(price, 2),
            "sentiment": self.latest_sentiment,
            "timestamp": time.time(),
            "latency_ms": round((time.time() - price_timestamp) * 1000, 2),
        }
        payload = json.dumps(order).encode() + MESSAGE_DELIMITER
        try:
            self.order_socket.sendall(payload)
            print(f"[Strategy] Sent {side} order for {symbol} @ {price:.2f}")
        except OSError:
            print("[Strategy] OrderManager unreachable, retrying.")
            self.order_socket = None


if __name__ == "__main__":
    run_strategy()
