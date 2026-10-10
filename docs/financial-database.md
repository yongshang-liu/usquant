# Multi-company financial database: phase 1

The target is a maintainable US-listed company financial database for research and teaching. This release provides a current issuer discovery seed, resumable companyfacts ingestion, provenance snapshots, coverage audits, and an annual US-GAAP pilot panel. It is **not yet a complete historical listed-company universe or four complete financial statements**.

## Tables in Sequel Ace

- `sec_directory_snapshots`: immutable directory snapshot identities and file locations.
- `sec_issuers`: CIK-based issuer registry, listing aliases/exchanges, first/last observed timestamps. Multiple share classes do not become multiple companies. Missing entries are retained; absence is not evidence of delisting.
- `sec_import_attempts`: attempts, progress, failures and unsupported metric coverage. A terminated attempt may remain `running`; a later run retries it. Run only one importer at a time.
- `financial_facts`: selected normalized US-GAAP metrics with original disclosure versions.
- `annual_panel`: one issuer × period end × observation cutoff; JSON contains eleven metrics, missingness reasons and each observed value's source accession/tag/unit. This is an initial panel, not a complete accounting dataset.

The directory can contain foreign issuers, funds and OTC listings. Do not call all discovered entries domestic operating companies. The present normalizer handles 10-K/10-Q US-GAAP; IFRS and 20-F/40-F are retained in raw snapshots but not yet normalized. `no_supported_metrics` means a successful snapshot without mapped metrics, not an empty financial statement.

## Run from the project directory

```sh
.venv/bin/python -m usquant.financial_database discover
.venv/bin/python -m usquant.financial_database fetch --limit 30
.venv/bin/python -m usquant.financial_database coverage
.venv/bin/python -m usquant.financial_database panel --start-year 2010
```

For all remaining directory entries, omit `--limit`. An interrupted run resumes by skipping completed issuers. New facts are appended idempotently; original snapshots and filing versions remain. Re-fetch completed companies when updating:

```sh
.venv/bin/python -m usquant.financial_database fetch --refresh
.venv/bin/python -m usquant.financial_database panel --start-year 2010
```

`--refresh --limit N` always selects the first N issuers in CIK order; it is a bounded test, not a rotating refresh queue. A full refresh requires omitting the limit. The importer stops on access/rate-limit or network failures. Other recorded failures remain pending. No scheduled job has been installed.

The SEC contact email is read from local `.env`; never committed. Raw snapshots and coverage reports are also local. Archive `data/sec` and the MySQL volume separately from GitHub source backups.

## Annual sample rules and limitations

All available history is retained. 2010 is only the default panel lower boundary. It is not a justified research sample start year. Examine coverage before writing a paper's sample selection rationale.

Annual duration observations must come from 10-K/10-K/A and span 330–400 days. Instant balance sheet observations use matching period ends. Quarterly and YTD durations are not summed. Fiscal transition periods outside that window are excluded and require separate handling. `period_end_year` means the calendar year containing the fiscal period end; it must not be called the company's reported fiscal-year label. Filing metadata's fiscal year can describe the reporting filing rather than a comparative observation.

Latest disclosure strictly before the cutoff date is selected. Tag preference follows `TAGS` in `fundamentals.py`; alias counts and selected tags are retained. Competing contexts remain null with an ambiguity reason. Missing values remain null, never zero. Values are decimal strings, preserving source precision. For arithmetic in MySQL, explicitly cast after inspecting units.

Today's SEC companyfacts cannot guarantee historical point-in-time completeness. Historical original filings, acceptance timestamps, issuer/security histories, custom and dimensional XBRL concepts, four-statement relationships, IFRS mapping, and broader accounting metrics remain required phases. A current directory does not resolve survivorship bias or ticker reuse. CIK identifies the reporting entity, not a timeless economic company or individual security.

## Official references

[SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) documents standard entity-wide facts, XBRL history and nightly bulk archives. Bulk archives are the preferred next step for broad historical discovery; the incremental client here limits itself to one request per second.

## Readable wide view

Run `sql/annual-panel-view.sql` in MySQL once, then refresh Sequel Ace's table list and select `annual_panel_readable` under views. Its eleven metrics are independent numeric columns. Use `ORDER BY symbol, period_end, cutoff` in queries for stable order. Dollar-valued metrics are USD, diluted EPS is USD/share, diluted shares is shares. NULL means missing or ambiguous; inspect the underlying payload for the reason. Display values use DECIMAL(38,8); original decimal strings and source metadata remain intact in the underlying table. No records are copied, so newly built panel rows appear automatically.
