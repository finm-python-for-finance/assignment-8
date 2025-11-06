import math

from shared_memory_utils import SharedPriceBook


def test_shared_memory_update_and_read():
    book = SharedPriceBook(
        symbols=["AAA", "BBB"], name="test_price_book", create=True, force_recreate=True
    )
    try:
        book.update("AAA", 101.25)
        book.update("BBB", 99.75)

        assert math.isclose(book.read("AAA"), 101.25)
        snapshot = book.snapshot()
        assert snapshot["BBB"] == 99.75
    finally:
        book.close()
        book.unlink()

