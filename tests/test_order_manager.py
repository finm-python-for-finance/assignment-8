import json
import socket
import threading
import time

from config import MESSAGE_DELIMITER
from order_manager import OrderManagerServer


def test_order_manager_receives_orders():
    received = []
    server = OrderManagerServer(host="127.0.0.1", port=0, on_order=received.append)
    port = server.server.getsockname()[1]
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        time.sleep(0.05)
        with socket.create_connection(("127.0.0.1", port)) as sock:
            order1 = {
                "symbol": "AAA",
                "side": "BUY",
                "quantity": 5,
                "price": 101.0,
                "sentiment": 70,
                "latency_ms": 12.3,
            }
            order2 = {
                "symbol": "BBB",
                "side": "SELL",
                "quantity": 8,
                "price": 99.5,
                "sentiment": 30,
                "latency_ms": 15.0,
            }
            payload = json.dumps(order1).encode() + MESSAGE_DELIMITER + json.dumps(order2).encode() + MESSAGE_DELIMITER
            sock.sendall(payload)
        time.sleep(0.1)
    finally:
        server.stop()
        thread.join(timeout=1)
    assert [order["symbol"] for order in received] == ["AAA", "BBB"]
