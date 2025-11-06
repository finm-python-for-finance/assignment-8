from __future__ import annotations

import contextlib
from multiprocessing import shared_memory
from typing import Dict, Iterable, List, Optional

import numpy as np

from config import SHARED_MEMORY_NAME, SYMBOLS


class SharedPriceBook:
    """
    Wrapper around multiprocessing.shared_memory.SharedMemory that stores one
    float per symbol. Prices default to NaN until the OrderBook publishes the
    first tick.
    """

    def __init__(
        self,
        symbols: Optional[Iterable[str]] = None,
        name: str = SHARED_MEMORY_NAME,
        create: bool = False,
        force_recreate: bool = False,
    ) -> None:
        self.symbols: List[str] = list(symbols) if symbols is not None else SYMBOLS
        self.name = name
        self._index = {symbol: idx for idx, symbol in enumerate(self.symbols)}
        size = len(self.symbols) * np.float64().nbytes

        if create:
            if force_recreate:
                self._try_cleanup_existing(name)
            try:
                self.shm = shared_memory.SharedMemory(
                    name=self.name, create=True, size=size
                )
            except FileExistsError:
                # Someone already created it – attach to the existing segment.
                self.shm = shared_memory.SharedMemory(name=self.name)
        else:
            self.shm = shared_memory.SharedMemory(name=self.name)

        self.array = np.ndarray(
            (len(self.symbols),), dtype=np.float64, buffer=self.shm.buf
        )
        if create:
            self.array[:] = np.nan

    def update(self, symbol: str, price: float) -> None:
        idx = self._index[symbol]
        self.array[idx] = price

    def read(self, symbol: str) -> float:
        idx = self._index[symbol]
        return float(self.array[idx])

    def snapshot(self) -> Dict[str, float]:
        return {symbol: float(self.array[idx]) for symbol, idx in self._index.items()}

    def close(self) -> None:
        self.shm.close()

    def unlink(self) -> None:
        with contextlib.suppress(FileNotFoundError):
            self.shm.unlink()

    @staticmethod
    def _try_cleanup_existing(name: str) -> None:
        with contextlib.suppress(FileNotFoundError):
            shm = shared_memory.SharedMemory(name=name)
            shm.close()
            shm.unlink()
