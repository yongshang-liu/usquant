# Raw financial archives: current workflow

The active workflow retains official SEC Financial Statement Data Set ZIP packages and checksum manifests only. Files are organized as `data/sec_raw/YYYY/Qn/SHA256/source.zip` and `manifest.json`. The version checksum prevents upstream revisions from overwriting earlier archives. Package time is submission batch time, not necessarily the fiscal reporting year. Company and industry fields remain inside the original source data; there are no per-company or per-industry copies.

The 2010 Q1 archive is present and checksum-verified. Older experimental companyfacts snapshots, panel/registry tables, and duplicate raw financial MySQL tables were deleted at the user's request. Uncompressed TXT copies were also removed to save storage. Market bars and backtest runs remain.

```sh
# Archive only; reuses and verifies an existing local package.
.venv/bin/python -m usquant.sec_raw --year 2010 --quarter 1
# Explicitly check for a revised upstream package.
.venv/bin/python -m usquant.sec_raw --year 2010 --quarter 1 --refresh
# Optional later step, only when ready to work in MySQL:
.venv/bin/python -m usquant.sec_raw --year 2010 --quarter 1 --import-mysql
```

No additional quarters or background imports are started automatically. `--import-mysql` extracts the four original files and creates raw tables plus readable views. Import is transactional and idempotent per checksum. Every source field remains a string, including blanks; no financial transformations are performed. Use the file's `adsh` report identity and batch identity for joins, plus `tag` and `version` for tag definitions. Do not sum multiple source revisions or let repeated PRE lines multiply numeric rows. `sql/raw-sec-views.sql` can add industry and reporting-period query views after import, if needed.

Historical normalized-panel documentation remains in the repository as an experimental reference, not a description of currently installed financial tables. Data archives and credentials are local, excluded from GitHub. Back up source ZIPs separately.

[SEC official download page](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets) documents dataset scope and quarterly updates. These are financial statement datasets, not all annual-report documents or footnotes.
