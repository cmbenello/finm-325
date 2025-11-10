from __future__ import annotations

import time

from config import SYMBOLS
from shared_memory_utils import SharedPriceBook

def main() -> None:
    book = SharedPriceBook(SYMBOLS, name="prices", create=True)
    print(f"[shm_init] created shared memory {book.name} for {SYMBOLS}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[shm_init] cleaning up")
        book.close()
        book.unlink()

if __name__ == "__main__":
    main()