from __future__ import annotations

from multiprocessing import Process

from config import SYMBOLS
from gateway import run_gateway
from orderbook import run_orderbook
from order_manager import run_ordermanager
from shared_memory_utils import SharedPriceBook
from strategy import run_strategy


def main() -> None:
    shm_name = "prices"
    book = SharedPriceBook(SYMBOLS, name=shm_name, create=True)
    print(f"[Main] created shared memory {book.name} for symbols {SYMBOLS}")

    procs = [
        Process(target=run_gateway, name="Gateway"),
        Process(target=run_orderbook, args=(shm_name,), name="OrderBook"),
        Process(target=run_strategy, args=(shm_name,), name="Strategy"),
        Process(target=run_ordermanager, name="OrderManager"),
    ]

    for p in procs:
        p.start()

    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        print("[Main] KeyboardInterrupt, terminating children")
    finally:
        for p in procs:
            if p.is_alive():
                p.terminate()
        book.close()
        book.unlink()
        print("[Main] cleaned up shared memory and exited")


if __name__ == "__main__":
    main()
