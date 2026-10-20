-- Layer 1: raw source files; layer 2: raw MySQL tables; layer 3: classification views.
CREATE OR REPLACE VIEW raw_sec_reports AS
SELECT b.package_year, b.package_quarter, s.batch_id, s.source_row,
       s.adsh, s.cik, NULLIF(s.sic,'') AS sic,
       CASE WHEN s.sic REGEXP '^[0-9]{1,4}$'
            THEN LPAD(s.sic,4,'0') ELSE NULL END AS sic_code,
       s.filed, s.period,
       JSON_UNQUOTE(JSON_EXTRACT(s.payload,'$.name')) AS company_name,
       JSON_UNQUOTE(JSON_EXTRACT(s.payload,'$.form')) AS form,
       JSON_UNQUOTE(JSON_EXTRACT(s.payload,'$.fy')) AS reported_fiscal_year,
       JSON_UNQUOTE(JSON_EXTRACT(s.payload,'$.fp')) AS fiscal_period,
       s.payload
FROM raw_sec_sub s JOIN raw_sec_batches b ON b.batch_id=s.batch_id;
-- Filing-year and package-year are distinct from report-period year.
SELECT package_year, package_quarter, COUNT(*) AS reports
FROM raw_sec_reports GROUP BY package_year,package_quarter;
SELECT sic_code, COUNT(*) AS reports FROM raw_sec_reports GROUP BY sic_code ORDER BY sic_code;
-- Use batch_id + adsh when joining reports and numbers. TAG joins also require version.
SELECT r.company_name,r.cik,r.sic_code,r.period,n.payload
FROM raw_sec_reports r JOIN raw_sec_num n ON n.batch_id=r.batch_id AND n.adsh=r.adsh
WHERE r.sic_code='3571' AND r.package_year=2010 LIMIT 20;
