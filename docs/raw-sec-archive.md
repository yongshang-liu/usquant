# Raw SEC archive organization

This archive is independent of the experimental normalized companyfacts panel. It stores original SEC quarterly Financial Statement Data Sets without financial metric mapping, panel construction, missing-value replacement, or restatement selection.

## Three layers

1. **Source archive:** `data/sec_raw/YYYY/Qn/SHA256/` contains `source.zip`, unchanged extracted `sub.txt`, `num.txt`, `tag.txt`, `pre.txt`, and `manifest.json`. A new upstream revision receives a new checksum directory; existing versions remain. The quarter is a filing-package quarter, not necessarily the financial reporting period.
2. **Raw MySQL tables:** `raw_sec_batches`, `raw_sec_sub`, `raw_sec_num`, `raw_sec_tag`, `raw_sec_pre`. Each imported source row has its batch checksum and line ordinal. `payload` preserves all source fields as strings including blanks. Selected SUB fields also appear as independent columns to enable classification; no source field is discarded. Files remain the authoritative originals.
3. **Classification view:** `raw_sec_reports` exposes the report's company, SIC code, filing date, reporting period, form, fiscal year and source package. Industry is associated with the report; a company's current industry must not replace its historical reported SIC. SIC blanks remain unclassified. No inferred industry names are assigned.

Keep source files organized by year and quarter, rather than duplicating originals into industry folders. Industry filtering is done through the report view. Avoid one physical table per industry/year: one consistent schema makes later joins easier. MySQL's internal files are managed by MySQL; do not rearrange Docker volume files in Finder.

## Download and import a quarter

```sh
.venv/bin/python -m usquant.sec_raw --year 2010 --quarter 1
```

Then run `sql/raw-sec-views.sql` in MySQL (its first statement installs the view, subsequent statements are example queries). All rows from all four files are imported transactionally; re-importing an identical checksum adds no rows. A revised source batch is kept separately. When combining revisions, deliberately choose batches before joining; do not sum all archived versions. Report-to-number joins use `batch_id + adsh`; tag joins require `batch_id + tag + version`. Presentation lines may repeat a tag, so direct joins with PRE can multiply numeric records.

The initial verified package is 2010 Q1. Other quarters are not downloaded automatically by this command. Missing sources or invalid ZIP/row/checksum errors stop the import. No background job or schedule is installed. Use a single importer at a time.

[Official SEC download page](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets) documents coverage, quarterly updates and the December 2024 reprocessing. The datasets represent filed financial-statement data, not every original filing document or all footnotes; coverage is not identical to every US-listed company.

## Teaching and inspection

In Sequel Ace select the `usquant` database, refresh the list, and open `raw_sec_reports` under Views. Filter on `sic_code` for industry, `package_year` for the source filing batch, or `period` for the report end. These are different time concepts. The `raw_sec_sub_readable`, `raw_sec_num_readable`, `raw_sec_tag_readable`, and `raw_sec_pre_readable` views expose original file fields as independent text columns. Their columns follow the currently installed package headers; a source header change requires inspecting and refreshing these views. Database exports are working copies; keep the original ZIP and checksum manifest as the recovery reference.
