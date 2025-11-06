"""
Central configuration for the IPC trading stack.
Adjust host/ports or trading parameters here instead of hard-coding them
throughout the individual processes.
"""

HOST = "127.0.0.1"
PRICE_FEED_PORT = 5101
NEWS_FEED_PORT = 5102
ORDER_MANAGER_PORT = 5103

MESSAGE_DELIMITER = b"*"

# Symbols to stream and track
SYMBOLS = ["AAPL", "MSFT", "GOOG"]

# Gateway behaviour
INITIAL_PRICES = {
    "AAPL": 173.2,
    "MSFT": 325.1,
    "GOOG": 135.8,
}
RANDOM_WALK_STD = 0.4
TICK_INTERVAL_SECONDS = 0.5

# Shared memory
SHARED_MEMORY_NAME = "pf_price_book"

# Strategy configuration
SHORT_WINDOW = 3
LONG_WINDOW = 6
BULLISH_THRESHOLD = 60
BEARISH_THRESHOLD = 40
ORDER_QUANTITY = 10
MAX_PRICE_HISTORY = LONG_WINDOW

# Logging / misc
DEFAULT_TIMEOUT = 5.0

