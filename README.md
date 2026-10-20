# USQuant — learning with QuantConnect LEAN

This project now follows **QuantConnect LEAN**. The old home-built engine is archived under `legacy/` and is no longer the active workflow. This is a learning workspace built around upstream LEAN, not an independently authored trading engine.

## Start here

1. Read [the learning path](docs/learning-path.md).
2. Explore the unchanged [official engine source](vendor/lean) or [upstream GitHub](https://github.com/QuantConnect/Lean).
3. Run the official Python example, then the first annotated exercise.
4. Inspect the actual LEAN logs, orders, charts and statistics under local `results/`.

```sh
git clone --recurse-submodules https://github.com/yongshang-liu/usquant.git
cd usquant
# For an existing checkout:
git submodule update --init --recursive

python3 scripts/run_lean.py official
python3 scripts/run_lean.py first
```

Docker Desktop must be running. The first command downloads the pinned official engine image: ARM64 for Apple silicon, AMD64 for Intel. The images are large (approximately 5 GB compressed for ARM64, 14 GB for AMD64 at the pinned version); extracted storage is larger. No QuantConnect account, CLI subscription or brokerage credentials are needed for these sample-data Docker backtests. Commercial cloud services and additional data are separate products.

## Layout

| Path | Purpose |
|---|---|
| `vendor/lean/` | Official complete engine checkout, pinned as a Git submodule; C# engine, Python examples, test data and upstream tests |
| `lessons/` | Small learning algorithms written against LEAN's Python API |
| `scripts/run_lean.py` | Thin Docker launcher, not a backtesting engine |
| `configs/engine-lock.json` | Pinned source and official binary image references |
| `results/` | Local logs, orders, statistics and charts; excluded from Git |
| `legacy/` | Previous implementation for reference only |
| `data/`, `.env` | Existing local archives/credentials retained; excluded from Git and not mounted into LEAN |

## Execution boundary

The supplied launcher exposes **offline backtesting only**, sets `live-mode=false`, removes live environments, disables container networking and passes no credentials. No real or broker-paper orders can be submitted by this launcher. A future broker-paper adapter will be designed and verified separately; real trading remains out of scope.

LEAN's core is C#, with Python strategy support. MySQL remains a storage source for later adapters; LEAN consumes its own file/data contracts. The previous MySQL data is preserved, but is not silently treated as native LEAN equity data, Morningstar fundamentals or verified corporate-action history.

## Provenance and attribution

Upstream is Apache-2.0 licensed. Its LICENSE and notices remain in the submodule; see [attribution](NOTICE). Source commit and prebuilt image digests are pinned independently. The image is not claimed to have been built from this exact checkout. Each local run records both references in `provenance.json`.

The pre-migration implementation is recoverable at tag `pre-lean-2026-10-20` and branch `archive/pre-lean-2026-10-20`. No database or secret was deleted during this migration.

Both the official example and Lesson 01 have completed real local LEAN backtests on Apple silicon; see [verification and limits](docs/verification.md).
