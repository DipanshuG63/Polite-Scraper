# Verification record — W5 A9 polite scraper

## Scope and source

- Source was the supplied `polite-scraper-main.zip` project.
- Requirements were checked against `W5 - The polite scraper.pdf` (7 required stages; first 3 catalogue pages and 60 products).
- The supplied `output/run-report.json` records a **historical cached run on 2026-10-06**. It reports 63 cache hits, 60 valid records, and zero failures. This was **not** rerun live in the editing environment.
- The saved 60-book snapshot has 60 unique HTTPS product URLs, nine required raw+normalized fields, and passes Pydantic validation.

## Changes made

1. Repaired legacy encoding artifacts in the saved text (e.g., `Â£` → `£`, corrupted curly apostrophes), without inventing or re-fetching data. Historical timestamps were retained.
2. Fetch real HTML as UTF-8, not `requests.Response.text`'s possible Latin-1 fallback.
3. Restrict all requests to the expected HTTPS practice-sandbox host; disable redirects; stop immediately on 403/404/429.
4. Keep >=500 ms between request starts, use timeout, identifying User-Agent, disk cache, and a single retry only for connection/timeouts/5xx.
5. Make the run report distinguish failed page requests from parsed-but-invalid records; do not silently return success when real pages fail.
6. Correct unique URL metrics: the deliberately fake test URL is tracked as a separate *attempt* rather than a discovered catalogue record.
7. Preserve fetch provenance on cache hit using the cache file timestamp rather than pretending the book was fetched just now.
8. Save JSON atomically and add offline pipeline/failure/cache tests and a GitHub Actions workflow.

## What was actually verified in this session

- `python -m pytest -q`: **18 passed** (offline).
- A deterministic 3-page mock catalogue with 20 distinct books per page yielded `catalogue_pages=3`, `discovered=60`, `unique_urls=60`.
- An offline full pipeline stored 60 valid unique records and repeated with the same 60 records, from cache.
- An appended fake 404 was isolated; the 60 real mock books were preserved; failed_pages was 1.
- An ordinary failed detail page (not an intentionally injected failure) produced a **non-zero** exit code and an honest 59-record report.
- Saved historical `output/books.json`: **60 unique records**, validated with the current schema. Its dates represent the old collection, not a fresh run.

## What could not be verified here

- A **fresh live end-to-end scrape** of https://books.toscrape.com is unverified in this restricted execution environment (network DNS unavailable). The supplied historical run evidence and mock tests are not a substitute for a current live run.
- A current live response from `/robots.txt` could not be fetched in the environment. The README distinguishes previously reported 404 observations from a new live check.

## Final live commands (run once on the user's machine after installing requirements)

```powershell
python -m src.classify
python -m src.main
python -m src.main
python -m src.main --include-broken-test
python -m pytest -q
```

Expected: first run 60 unique books across 3 pages, second run mostly `CACHE HIT`, and the broken test run retains 60 valid records with `failed_pages=1`. All real requests include a 500 ms minimum delay and are cached on disk.

The site itself is an explicitly designated practice sandbox: https://sites.toscrape.com/.
