from __future__ import annotations

import socket
import time
from multiprocessing.synchronize import Lock
from typing import Optional

from config import HOST, MESSAGE_DELIMITER, PRICE_FEED_PORT, SYMBOLS, SHARED_MEMORY_NAME
from shared_memory_utils import SharedPriceBook


def run_orderbook(
    lock: Optional[Lock] = None,
    host: str = HOST,
    port: int = PRICE_FEED_PORT,
    symbols=None,
    shared_name: Optional[str] = None,
    force_recreate: bool = True,
) -> None:
    symbols = symbols or SYMBOLS
    shared_prices = SharedPriceBook(
        symbols,
        name=shared_name or SHARED_MEMORY_NAME,
        create=True,
        force_recreate=force_recreate,
    )
    try:
        _pump_prices(shared_prices, lock, host, port)
    finally:
        shared_prices.close()


def _pump_prices(
    price_book: SharedPriceBook, lock: Optional[Lock], host: str, port: int
) -> None:
    while True:
        try:
            sock = socket.create_connection((host, port))
            print("[OrderBook] Connected to price feed.")
            _recv_loop(sock, price_book, lock)
        except ConnectionRefusedError:
            print(f"[OrderBook] Price feed {host}:{port} unavailable, retrying in 1s.")
            time.sleep(1)
        except KeyboardInterrupt:
            break


def _recv_loop(sock: socket.socket, price_book: SharedPriceBook, lock: Optional[Lock]):
    buffer = b""
    with sock:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                print("[OrderBook] Connection closed by gateway, reconnecting.")
                break
            buffer += chunk
            while True:
                delimiter_index = buffer.find(MESSAGE_DELIMITER)
                if delimiter_index == -1:
                    break
                token = buffer[:delimiter_index]
                buffer = buffer[delimiter_index + len(MESSAGE_DELIMITER) :]
                if not token:
                    continue
                _handle_price_token(token, price_book, lock)


def _handle_price_token(
    token: bytes, price_book: SharedPriceBook, lock: Optional[Lock]
) -> None:
    try:
        decoded = token.decode()
        symbol, price_str = decoded.split(",")
        price = float(price_str)
        if lock:
            with lock:
                price_book.update(symbol, price)
        else:
            price_book.update(symbol, price)
    except ValueError:
        print(f"[OrderBook] Could not parse token: {token!r}")


if __name__ == "__main__":
    run_orderbook()
