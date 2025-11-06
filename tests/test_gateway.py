import socket
import time

from config import MESSAGE_DELIMITER, SYMBOLS
from gateway import GatewayServer


def test_gateway_accepts_clients_and_streams():
    server = GatewayServer(host="127.0.0.1", price_port=0, news_port=0, tick_interval=0.01)
    try:
        server.price_accept_thread.start()
        server.news_accept_thread.start()

        price_port = server.price_server.getsockname()[1]
        news_port = server.news_server.getsockname()[1]

        with socket.create_connection(("127.0.0.1", price_port)) as price_client, socket.create_connection(
            ("127.0.0.1", news_port)
        ) as news_client:
            time.sleep(0.1)
            assert server._price_clients, "Gateway did not register price client"
            assert server._news_clients, "Gateway did not register news client"

            price_client.settimeout(1)
            news_client.settimeout(1)

            server.broadcast_prices()
            price_data = price_client.recv(1024)
            assert price_data.endswith(MESSAGE_DELIMITER)
            assert price_data.count(MESSAGE_DELIMITER) >= len(SYMBOLS)

            server.broadcast_news()
            news_data = news_client.recv(1024)
            assert news_data.endswith(MESSAGE_DELIMITER)
    finally:
        server.stop()
