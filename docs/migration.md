# Migration to LEAN, 20 October 2026

The user requested replacing the previous implementation and learning LEAN systematically. LEAN is now the active engine, not a comparison dependency attached to the previous simulator.

## Preserved

- Git tag `pre-lean-2026-10-20` and branch `archive/pre-lean-2026-10-20` identify the exact previous tracked implementation.
- Previous tracked source, configs, docs and workflows are under `legacy/` for reference. Archived workflow files are not active GitHub Actions workflows.
- Local `.env`, market/SEC snapshots, reports and MySQL contents remain. They are not in the Git archive because they were never committed. Back them up separately.
- The existing MySQL container was not stopped, reset or recreated. The old Compose file moved to `legacy/compose.yaml`; do not run it from its new location without reviewing its paths/project name. Its named volume is not part of the source checkout.

## Active now

- Official upstream engine and sample data in pinned `vendor/lean` submodule.
- Direct use of the official ARM64/AMD64 Docker binary images. No package or engine imitation is substituted for LEAN.
- One original upstream Python example plus one small learner algorithm.
- Offline-only runner with per-run logs, configuration and source/image provenance.
- A new static-check workflow; real runtime verification is performed locally and documented separately. Static checks must not be presented as full upstream regression tests.

## Not migrated yet

The old factor simulator, ad hoc risk model, local paper journal and raw financial mappings are not wired into the new entry point. The previous MySQL database is retained as source material, not automatically imported. Native LEAN data adapters, financial-factor exercises and broker-paper connection are subsequent lessons. No real trading, unattended loop or new recurring automation was enabled.

Do not delete the Git submodule and copy its code without license/provenance records. Do not run archived instructions as if they describe the new workspace.
