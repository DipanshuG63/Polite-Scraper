# The Polite Scraper — FlyRank W5 Assignment A9

Python 3.10+ pipeline for the explicitly authorized **[Books to Scrape](https://books.toscrape.com/)** educational sandbox. From **exactly the first three catalogue pages**, it discovers 60 unique books, fetches detail HTML politely, extracts eight raw fields plus numeric `price_gbp`, validates with **Pydantic**, writes JSON, and reports failures without losing good books.

**Project origin:** reviewed and improved from the supplied `polite-scraper-main.zip`. See [verification record](docs/verification.md) for measured checks and limitations.

## Run in five minutes

Requires Python 3.10+ and an internet connection for the first run.

```powershell
py -m pip install -r requirements.txt
py -m src.main
```

On Linux/macOS use `python3` instead of `py`. After the first run, all 63 successful HTML pages are cached; rerunning `py -m src.main` should print `CACHE HIT` for those pages and produce **60** unique records again. All outputs are under `output/`.

For a deliberately broken page (it is requested **once**, not hammered):

```powershell
py -m src.main --include-broken-test
```

Expected: 60 valid books, one 404 in `output/errors.json`, and `failed_pages: 1` in `output/run-report.json`. An unexpected live failure instead causes a nonzero exit status, while still reporting whatever succeeded.

Unit and offline end-to-end tests (no external requests):

```powershell
py -m pytest -q
```

## Target classification (Stage 0)

- **Site and permission:** the [official ToScrape sandbox listing](https://sites.toscrape.com/) explicitly describes Books to Scrape as a fictional bookstore for practicing web scraping. This exercise **only targets that sandbox**. The site serves HTML without a JavaScript browser.
- **Scope:** first **3** catalogue pages, following each page's actual `next` link; the expected 20 products per page yields **60** unique detail pages. **No more catalogue pages** are visited.
- **Fields collected:** title, product URL, price text, availability text, rating text, description, source catalogue page, and fetch time, plus normalized GBP price.
- **Robots.txt check:** past public observations report **HTTP 404** for `https://books.toscrape.com/robots.txt` (no robots file found). That is **not a grant of permission**; the site's own sandbox description is the relevant authorization. Run `py -m src.classify` once to check its current response yourself. This project's isolated verification environment could **not** reach that endpoint for a fresh confirmation.

**I will not reuse this code on another site without checking its rules and terms first.**

## Politeness and reliability

1. An identifying `User-Agent`: `FlyRankInternship-A9/1.0 (+https://github.com/DipanshuG63)`.
2. At least **500 ms** between the starts of all real requests; **no delay on cache hits**.
3. A **10-second timeout**, status check, and no following redirects to other sites.
4. A single retry after a brief pause for timeouts, connection errors or **5xx**; **no retry** on 403, 404 or 429.
5. Cache saved HTML locally: page 1 at `cache/catalogue-page-1.html`, subsequent catalogue pages at `cache/catalogue-page-2.html` and `cache/catalogue-page-3.html`; book HTML by URL hash to avoid collisions. The cache directory is git-ignored.
6. A separate error entry per bad page, with a reason; never discard the other validated records.
7. All requested URLs must be HTTPS on `books.toscrape.com`, even when discovered from a page.

## Schema: one output/books.json record

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-10-06T21:24:49.986582Z"
}
```

`description` is **nullable** (`null` where missing); it is never invented. Exact description text may vary. Every `BookRecord` is checked with Pydantic **before** storage. Its absolute `product_url` serves as a unique key (no duplicate records); the two provenance fields identify the source page and time of retrieval. Prices are numeric GBP amounts and also keep the original `price_text`.

### Output files

| Path | Purpose |
|---|---|
| `output/books.json` | Valid, unique books only, with provenance |
| `output/errors.json` | Invalid records or failed page fetches, with stage/reason |
| `output/run-report.json` | Start time, duration, fetched/cache counts, valid/invalid counts, failed-page count, discovery counts |
| `output/books.sample.json` | Example record shape |
| `docs/verification.md` | Explicitly distinguishes live historical evidence from offline tests |

## Historical run report supplied with the project

The following is an **actual historical cached-run report** from 6 October 2026, included in the uploaded ZIP. It has **not** been falsely presented as a new live run. After a fresh run on your laptop, `output/run-report.json` is overwritten with that run's actual values.

```json
{
  "start_time": "2026-10-06T21:24:49.907609+00:00",
  "duration_seconds": 0.526,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_urls": [],
  "catalogue_scope": 3,
  "unique_book_urls": 60
}
```

### Verification of the updated version

The improved project passed **18 offline tests** in the preparation environment, including 60-record discovery and rerun via deterministic fixtures, 404 failure isolation, one-retry checks, UTF-8 handling, URL restrictions, and Pydantic validation of all 60 saved real-book records. The saved `books.json` from the previous run has **60 unique records**; corrupted legacy text (`Â£`, apostrophes) was repaired without changing the provenance dates. A **fresh live scrape and current robots check remain to be run** from a network-enabled machine. Details: [docs/verification.md](docs/verification.md).

## Why no browser?

Books to Scrape renders book information directly in the HTML sent by the server. `requests` plus Beautiful Soup are sufficient; loading a full browser would only add overhead for this task.

## Ethics

When available, prefer an official API. Never bypass logins, paywalls, blocks or access controls. Honor site rules, avoid unnecessary collection, identify the client, rate-limit requests, and cache responses rather than continuously re-downloading them.

## Honest limitation

The website may change selectors or go offline. The pipeline reports those failures, rather than inventing missing fields or silently claiming success. The example 60-book output is an older verified snapshot; re-run on an internet-enabled machine for fresh data.

## Seven stages and meaningful Git commits

| Stage | Implementation |
|---|---|
| 0 — Classify | Sandbox scope, robots documentation and safety note |
| 1 — Fetch | Identifying user-agent, timeouts, pacing and disk cache |
| 2 — Discover | Relative-to-absolute URLs and first three catalogue pages |
| 3 — Extract | Detail selectors, nullable descriptions and provenance |
| 4 — Validate/store | Pydantic, price normalization, unique 60-book output |
| 5 — Survive/report | Per-page failure isolation, 404 exercise and run report |
| 6 — Publish | This README, tests, evidence and publishing instructions |

`git log --oneline` shows all seven incremental stage commits in the prepared project ZIP's Git history. The ZIP has a real `.git` directory; follow `PUBLISH_TO_GITHUB_WINDOWS.txt` after creating the **separate** public `polite-scraper` repository in your GitHub account.
