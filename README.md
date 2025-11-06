# IPC Trading Stack

Multi-process trading simulation that mirrors a miniature trading desk:

```
[ Gateway ] -> [ OrderBook ] -> (Shared Memory) -> [ Strategy ] -> [ OrderManager ]
                    ^                               |
                    |-------- news sentiment -------|
```

## Features
- Gateway streams random-walk prices plus random news sentiment over TCP sockets.
- OrderBook consumes prices and writes them into a NumPy-backed shared memory segment protected by a lock.
- Strategy reads shared memory, ingests news, runs a moving-average crossover + sentiment filter, and sends orders only when both agree.
- OrderManager is a TCP server that logs deserialized orders in real time.
- `main.py` orchestrates all processes with the Windows-safe `spawn` context.

## Getting Started

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Run the full stack

```bash
python main.py
```

Stop with `Ctrl+C`. Each process logs to the console; keep the window wide enough to see the interleaved output.

### Run individual components

```bash
python gateway.py
python orderbook.py
python strategy.py
python order_manager.py
```

These commands are useful when recording the demo video because you can place each in its own terminal.

### Tests

```bash
pytest
```

Tests cover shared-memory propagation and strategy signal logic.

## Configuration

All tunables (ports, symbols, thresholds, rolling-window sizes, etc.) live in `config.py`. Update that file to add symbols or tweak behaviour. Ensure you delete the shared memory segment (or let `OrderBook` recreate it) when changing symbol counts.

## Measuring Performance

See `performance_report.md` for the latest numbers plus methodology. In short:
1. Use `scripts/` snippets (or `nc`) to connect to each socket and measure throughput.
2. Capture strategy logs filtered on `Sent order` to derive latency between a price tick and an order decision.
3. Shared memory footprint is deterministic: `len(SYMBOLS) * 8 bytes`.

## Video
