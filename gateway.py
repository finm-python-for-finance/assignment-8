from __future__ import annotations

import contextlib
import random
import socket
import threading
import time
from typing import Dict, Optional, Set

from config import (
    HOST,
    INITIAL_PRICES,
    MESSAGE_DELIMITER,
    NEWS_FEED_PORT,
    PRICE_FEED_PORT,
    RANDOM_WALK_STD,
    SYMBOLS,
    TICK_INTERVAL_SECONDS,
)


class GatewayServer:
    def __init__(
        self,
        host: str = HOST,
        price_port: int = PRICE_FEED_PORT,
        news_port: int = NEWS_FEED_PORT,
        tick_interval: float = TICK_INTERVAL_SECONDS,
    ) -> None:
        self.host = host
        self.price_port = price_port
        self.news_port = news_port
        self.tick_interval = tick_interval
        self.price_prices: Dict[str, float] = INITIAL_PRICES.copy()
        self.delimiter_text = MESSAGE_DELIMITER.decode()
        self._price_clients: Set[socket.socket] = set()
        self._news_clients: Set[socket.socket] = set()
        self._stop = threading.Event()
        self._price_lock = threading.Lock()
        self._news_lock = threading.Lock()

        self.price_server = self._build_server_socket(self.price_port)
        self.news_server = self._build_server_socket(self.news_port)

        self.price_accept_thread = threading.Thread(
            target=self._accept_loop,
            args=(self.price_server, self._price_clients, self._price_lock, "price"),
            daemon=True,
        )
        self.news_accept_thread = threading.Thread(
            target=self._accept_loop,
            args=(self.news_server, self._news_clients, self._news_lock, "news"),
            daemon=True,
        )

    def _build_server_socket(self, port: int) -> socket.socket:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, port))
        server.listen()
        server.settimeout(1.0)
        return server

    def _accept_loop(
        self,
        server: socket.socket,
        client_set: Set[socket.socket],
        lock: threading.Lock,
        label: str,
    ) -> None:
        while not self._stop.is_set():
            try:
                conn, addr = server.accept()
                conn.setblocking(False)
                with lock:
                    client_set.add(conn)
                print(f"[Gateway] {label} client connected: {addr}")
            except socket.timeout:
                continue
            except OSError:
                break

    def broadcast_prices(self) -> None:
        message = self._serialize_prices().encode()
        self._broadcast(message, self._price_clients, self._price_lock)

    def broadcast_news(self) -> None:
        sentiment = random.randint(0, 100)
        payload = f"{sentiment}".encode()
        self._broadcast(payload, self._news_clients, self._news_lock)

    def _broadcast(
        self,
        payload: bytes,
        client_set: Set[socket.socket],
        lock: threading.Lock,
    ) -> None:
        data = payload + MESSAGE_DELIMITER
        disconnected: List[socket.socket] = []
        with lock:
            for client in list(client_set):
                try:
                    client.sendall(data)
                except OSError:
                    disconnected.append(client)
            for client in disconnected:
                client_set.remove(client)
                with contextlib.suppress(OSError):
                    client.close()

    def _serialize_prices(self) -> str:
        entries = []
        for symbol in SYMBOLS:
            price = self._next_price(symbol)
            entries.append(f"{symbol},{price:.2f}")
        return self.delimiter_text.join(entries)

    def _next_price(self, symbol: str) -> float:
        current = self.price_prices.get(symbol, INITIAL_PRICES[symbol])
        delta = random.gauss(0, RANDOM_WALK_STD)
        new_price = max(0.01, current + delta)
        self.price_prices[symbol] = new_price
        return new_price

    def run(self) -> None:
        self.price_accept_thread.start()
        self.news_accept_thread.start()
        print("[Gateway] Started price and news streams.")
        tick_count = 0
        try:
            while not self._stop.is_set():
                self.broadcast_prices()
                self.broadcast_news()
                tick_count += 1
                time.sleep(self.tick_interval)
        except KeyboardInterrupt:
            print("[Gateway] Shutting down.")
        finally:
            self._stop.set()
            self.price_server.close()
            self.news_server.close()
            for client in list(self._price_clients) + list(self._news_clients):
                with contextlib.suppress(OSError):
                    client.close()

    def stop(self) -> None:
        self._stop.set()
        with contextlib.suppress(OSError):
            self.price_server.close()
            self.news_server.close()


def run_gateway(
    host: str = HOST,
    price_port: int = PRICE_FEED_PORT,
    news_port: int = NEWS_FEED_PORT,
    tick_interval: float = TICK_INTERVAL_SECONDS,
    max_ticks: Optional[int] = None,
) -> None:
    server = GatewayServer(host=host, price_port=price_port, news_port=news_port, tick_interval=tick_interval)
    if max_ticks is None:
        server.run()
        return

    server.price_accept_thread.start()
    server.news_accept_thread.start()
    print("[Gateway] Started price and news streams (bounded run).")
    processed = 0
    try:
        while processed < max_ticks:
            server.broadcast_prices()
            server.broadcast_news()
            processed += 1
            time.sleep(tick_interval)
    finally:
        server.stop()


if __name__ == "__main__":
    run_gateway()
