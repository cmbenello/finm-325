"""Shared memory utilities for storing latest prices of symbols."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import numpy as np
from multiprocessing import shared_memory, Lock


class SharedPriceBook:
    def __init__(
        self,
        symbols: Iterable[str],
        name: Optional[str] = None,
        create: bool = True,
        lock: Optional[Lock] = None,
    ) -> None:
        self.symbols: List[str] = list(symbols)
        if not self.symbols:
            raise ValueError("SharedPriceBook requires at least one symbol")

        self.symbol_to_idx: Dict[str, int] = {
            sym: i for i, sym in enumerate(self.symbols)
        }

        self._dtype = np.float64
        self._n = len(self.symbols)
        self._lock = lock

        nbytes = self._n * np.dtype(self._dtype).itemsize

        if create:
            self.shm = shared_memory.SharedMemory(name=name, create=True, size=nbytes)
            self.array = np.ndarray((self._n,), dtype=self._dtype, buffer=self.shm.buf)
            self.array[:] = np.nan
        else:
            if name is None:
                raise ValueError("Must supply a shared memory name when create=False")
            self.shm = shared_memory.SharedMemory(name=name, create=False)
            self.array = np.ndarray((self._n,), dtype=self._dtype, buffer=self.shm.buf)

    def update(self, symbol: str, price: float) -> None:
        try:
            idx = self.symbol_to_idx[symbol]
        except KeyError as exc:
            raise KeyError(f"Unknown symbol in SharedPriceBook.update: {symbol!r}") from exc

        if self._lock is not None:
            with self._lock:
                self.array[idx] = float(price)
        else:
            self.array[idx] = float(price)

    def read(self, symbol: str) -> float:
        try:
            idx = self.symbol_to_idx[symbol]
        except KeyError as exc:
            raise KeyError(f"Unknown symbol in SharedPriceBook.read: {symbol!r}") from exc

        if self._lock is not None:
            with self._lock:
                value = float(self.array[idx])
        else:
            value = float(self.array[idx])
        return value

    def read_all(self) -> Dict[str, float]:
        if self._lock is not None:
            with self._lock:
                data = {sym: float(self.array[i]) for i, sym in enumerate(self.symbols)}
        else:
            data = {sym: float(self.array[i]) for i, sym in enumerate(self.symbols)}
        return data

    def close(self) -> None:
        self.shm.close()

    def unlink(self) -> None:
        self.shm.unlink()

    @property
    def name(self) -> str:
        return self.shm.name

    @property
    def nbytes(self) -> int:
        return self.array.nbytes

    def __repr__(self) -> str:
        return (
            f"SharedPriceBook(name={self.shm.name!r}, "
            f"symbols={self.symbols!r})"
        )


def _self_test() -> None:
    symbols = ["AAPL", "MSFT"]

    book_creator = SharedPriceBook(symbols, name="finm325_prices", create=True)
    print("Created shared price book:", book_creator)

    book_creator.update("AAPL", 123.45)
    book_creator.update("MSFT", 234.56)

    book_reader = SharedPriceBook(symbols, name=book_creator.name, create=False)
    print("Attached reader book:", book_reader)

    print("Reader sees prices:", book_reader.read_all())

    book_reader.close()
    book_creator.close()
    book_creator.unlink()


if __name__ == "__main__":
    _self_test()
