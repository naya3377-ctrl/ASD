# 0.2.0 → 0.3.0 render transport comparison

2026-09-25, Linux x64, Python 3.12, PySide6 6.8.3, PyMuPDF 1.26.6.
Self-created `samples/sample.pdf`, normal page 1 and scanned page 4.
Each case: one warm-up, six timed iterations, median milliseconds.
Timing includes page rendering, worker-to-GUI transfer, QImage decoding/copy.
It excludes process startup, document opening, QML layout, GPU presentation and disk cold-cache effects.
These numbers do not predict all PDFs or Windows hardware.

| Page | Width | 0.2.0 PNG | 0.3.0 shared frames |
|---|---:|---:|---:|
| Normal | 1600 px | 81.61 ms | 6.90 ms |
| Scan | 1600 px | 121.61 ms | 48.20 ms |
| Normal | 3000 px | 288.08 ms | 43.58 ms |
| Scan | 3000 px | 303.01 ms | 58.23 ms |

To repeat, extract 0.2.0 source and set `BICHAEK_BASELINE` to its project directory.
Run `python scripts/benchmark_transport.py`. Raw observations are in `transport-results.json`.
