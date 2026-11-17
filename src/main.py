"""Seven-stage polite scraper. Run using: python -m src.main"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

if __package__:
    from .fetcher import PoliteFetcher
    from .models import BookRecord
    from .parser import extract_book, extract_catalogue_links
else:  # Preserve the original `python src/main.py` invocation.
    from fetcher import PoliteFetcher
    from models import BookRecord
    from parser import extract_book, extract_catalogue_links

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/DipanshuG63)"
BROKEN_TEST_URL = "https://books.toscrape.com/catalogue/this-page-does-not-exist_999999/index.html"


def write_json(path: Path, payload) -> None:
    """Keep valid JSON outputs even if the program is interrupted mid-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def discover(fetcher: PoliteFetcher) -> tuple[list[tuple[str, str]], dict[str, int]]:
    page_url = START_URL
    discovered: list[tuple[str, str]] = []
    seen_pages: set[str] = set()
    while page_url and len(seen_pages) < 3:
        fetcher._check_url(page_url)
        if page_url in seen_pages:
            raise ValueError("Catalogue pagination contains a cycle")
        seen_pages.add(page_url)
        html, marker = fetcher.get(page_url, cache_key=f"catalogue-page-{len(seen_pages)}")
        print(f"{marker}: {page_url} ({len(html.encode('utf-8'))} bytes)")
        links, next_url = extract_catalogue_links(html, page_url)
        for link in links:
            fetcher._check_url(link)
            discovered.append((link, page_url))
        page_url = next_url

    unique: dict[str, str] = {}
    for product_url, source_page in discovered:
        unique.setdefault(product_url, source_page)
    metrics = {"catalogue_pages": len(seen_pages), "discovered": len(discovered), "unique_urls": len(unique)}
    print(", ".join(f"{k}={v}" for k, v in metrics.items()))
    return list(unique.items()), metrics


def run(include_broken: bool = False, fetcher: PoliteFetcher | None = None, output_dir: Path | None = None) -> int:
    started = time.monotonic()
    started_at = datetime.now(timezone.utc)
    fetcher = fetcher or PoliteFetcher(CACHE_DIR, USER_AGENT, timeout=10, delay=0.5)
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    valid: dict[str, dict] = {}
    errors: list[dict] = []
    failed_pages: list[str] = []
    invalid_records = 0
    metrics = {"catalogue_pages": 0, "discovered": 0, "unique_urls": 0}

    try:
        targets, metrics = discover(fetcher)
    except Exception as exc:
        report = {
            "start_time": started_at.isoformat(),
            "duration_seconds": round(time.monotonic() - started, 3),
            "pages_fetched": fetcher.stats.pages_fetched,
            "cache_hits": fetcher.stats.cache_hits,
            "valid_records": 0,
            "invalid_records": 0,
            "failed_pages": 1,
            "failed_urls": [],
            "discovery_error": str(exc),
            **metrics,
        }
        write_json(output_dir / "run-report.json", report)
        print(json.dumps(report, indent=2))
        return 1

    if include_broken:
        targets.append((BROKEN_TEST_URL, START_URL))

    for product_url, source_page in targets:
        try:
            html, marker = fetcher.get(product_url)
            print(f"{marker}: {product_url} ({len(html.encode('utf-8'))} bytes)")
        except Exception as exc:
            failed_pages.append(product_url)
            errors.append({"product_url": product_url, "stage": "fetch", "reason": str(exc)})
            print(f"FAILED FETCH: {product_url} -> {exc}")
            continue

        try:
            fetched_at = fetcher.fetched_at.get(product_url, datetime.now(timezone.utc).isoformat())
            raw = extract_book(html, product_url, source_page, fetched_at)
            record = BookRecord.model_validate(raw)
            valid[str(record.product_url)] = record.as_json_dict()
        except (ValueError, ValidationError, TypeError) as exc:
            invalid_records += 1
            errors.append({"product_url": product_url, "stage": "validation", "reason": str(exc)})
            print(f"INVALID: {product_url} -> {exc}")

    books = sorted(valid.values(), key=lambda item: item["product_url"])
    write_json(output_dir / "books.json", books)
    write_json(output_dir / "errors.json", errors)
    report = {
        "start_time": started_at.isoformat(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "pages_fetched": fetcher.stats.pages_fetched,
        "cache_hits": fetcher.stats.cache_hits,
        "valid_records": len(books),
        "invalid_records": invalid_records,
        "failed_pages": len(failed_pages),
        "failed_urls": failed_pages,
        **metrics,
        "attempted_detail_urls": len(targets),
    }
    write_json(output_dir / "run-report.json", report)
    print(json.dumps(report, indent=2))

    # A failed live scrape is never silently reported as a successful run.
    expected_failures = 1 if include_broken else 0
    complete = (metrics["catalogue_pages"] == 3 and metrics["unique_urls"] == 60
                and len(books) == 60 and invalid_records == 0
                and len(failed_pages) == expected_failures)
    return 0 if complete else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="FlyRank W5 A9 polite scraper")
    parser.add_argument("--include-broken-test", action="store_true", help="append one fake in-sandbox URL to prove failure isolation")
    args = parser.parse_args()
    raise SystemExit(run(include_broken=args.include_broken_test))


if __name__ == "__main__":
    main()
