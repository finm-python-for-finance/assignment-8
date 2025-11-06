from __future__ import annotations

import multiprocessing as mp

from gateway import run_gateway
from order_manager import run_ordermanager
from orderbook import run_orderbook
from strategy import run_strategy


def main() -> None:
    ctx = mp.get_context("spawn")
    price_lock = ctx.Lock()

    process_specs = [
        ("OrderManager", run_ordermanager, ()),
        ("Gateway", run_gateway, ()),
        ("OrderBook", run_orderbook, (price_lock,)),
        ("Strategy", run_strategy, (price_lock,)),
    ]

    processes = []
    for name, target, args in process_specs:
        process = ctx.Process(target=target, name=name, args=args)
        process.start()
        processes.append(process)

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("[Main] Terminating child processes...")
        for process in processes:
            process.terminate()
    finally:
        for process in processes:
            process.join()


if __name__ == "__main__":
    main()

