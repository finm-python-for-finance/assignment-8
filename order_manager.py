from __future__ import annotations

import contextlib
import json
import socket
import threading
from typing import Callable, List, Optional

from config import HOST, MESSAGE_DELIMITER, ORDER_MANAGER_PORT

OrderHandler = Callable[[dict], None]


class OrderManagerServer:
    def __init__(
        self,
        host: str = HOST,
        port: int = ORDER_MANAGER_PORT,
        on_order: Optional[OrderHandler] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.on_order = on_order
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen()
        self.server.settimeout(1.0)
        self._stop = threading.Event()

    def run(self) -> None:
        print(f"[OrderManager] Listening for orders on {self.host}:{self.port}.")
        clients: List[threading.Thread] = []
        try:
            while not self._stop.is_set():
                try:
                    conn, addr = self.server.accept()
                    print(f"[OrderManager] Client connected {addr}")
                    thread = threading.Thread(
                        target=self._handle_client, args=(conn,), daemon=True
                    )
                    thread.start()
                    clients.append(thread)
                except socket.timeout:
                    continue
                except OSError:
                    break
        except KeyboardInterrupt:
            print("[OrderManager] Shutting down.")
        finally:
            self.stop()
            for client in clients:
                client.join(timeout=1)

    def _handle_client(self, conn: socket.socket) -> None:
        buffer = b""
        with conn:
            while not self._stop.is_set():
                try:
                    chunk = conn.recv(4096)
                except OSError:
                    return
                if not chunk:
                    return
                buffer += chunk
                while True:
                    idx = buffer.find(MESSAGE_DELIMITER)
                    if idx == -1:
                        break
                    token = buffer[:idx]
                    buffer = buffer[idx + len(MESSAGE_DELIMITER) :]
                    if token:
                        self._log_order(token)

    def _log_order(self, token: bytes) -> None:
        try:
            order = json.loads(token.decode())
            if self.on_order:
                self.on_order(order)
            print(
                "[OrderManager] "
                f"{order.get('side')} {order.get('quantity')} {order.get('symbol')} @ "
                f"{order.get('price')} (sentiment={order.get('sentiment')}, "
                f"latency_ms={order.get('latency_ms')})"
            )
        except json.JSONDecodeError:
            print(f"[OrderManager] Invalid order payload: {token!r}")

    def stop(self) -> None:
        self._stop.set()
        with contextlib.suppress(OSError):
            self.server.close()


def run_ordermanager(
    host: str = HOST,
    port: int = ORDER_MANAGER_PORT,
) -> None:
    server = OrderManagerServer(host=host, port=port)
    server.run()


if __name__ == "__main__":
    run_ordermanager()
