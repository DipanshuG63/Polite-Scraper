"""Offline end-to-end checkpoints: never contact a live website."""
import json
from pathlib import Path

import pytest

from src.fetcher import PoliteFetcher, FetchStats
from src.main import BROKEN_TEST_URL, START_URL, discover, run
from src.models import BookRecord
from src.parser import extract_book, normalize_price

PREFIX = "https://books.toscrape.com/catalogue/"


def catalogue_html(page_number):
    items = "".join(
        f'<article class="product_pod"><h3><a href="mock-book-{i}_1/index.html">Book</a></h3></article>'
        for i in range((page_number - 1) * 20 + 1, page_number * 20 + 1)
    )
    nxt = f'<li class="next"><a href="page-{page_number + 1}.html">next</a></li>' if page_number < 3 else ""
    return f'<html><body>{items}<ul>{nxt}</ul></body></html>'


def book_html(i):
    description = '<div id="product_description">Description</div><p>Nice book</p>' if i % 2 else ''
    return (f'<article class="product_page"><div class="product_main">'
            f'<h1>Book {i}</h1><p class="price_color">£12.50</p>'
            f'<p class="instock availability">In stock (5 available)</p>'
            f'<p class="star-rating Three">Three</p></div>{description}</article>')


class FakeFetcher:
    """Deterministic simulated 3-page site, including optional isolated failures."""
    def __init__(self, broken_book=None):
        self.stats = FetchStats()
        self.fetched_at = {}
        self.cache = {}
        self.broken_book = broken_book

    _check_url = staticmethod(PoliteFetcher._check_url)

    def get(self, url, cache_key=None):
        self._check_url(url)
        if url in self.cache:
            self.stats.cache_hits += 1
            return self.cache[url], "CACHE HIT"
        if url == BROKEN_TEST_URL or url == self.broken_book:
            raise RuntimeError("HTTP 404")
        if url.startswith(PREFIX + "page-"):
            page = int(url.removeprefix(PREFIX + "page-").removesuffix(".html"))
            html = catalogue_html(page)
        else:
            i = int(url.removeprefix(PREFIX + "mock-book-").split("_")[0])
            html = book_html(i)
        self.cache[url] = html
        self.stats.pages_fetched += 1
        self.fetched_at[url] = "2026-11-18T00:00:00+00:00"
        return html, "FETCH"


def test_offline_full_pipeline_and_rerun(tmp_path):
    fake = FakeFetcher()
    targets, report = discover(fake)
    assert report == {"catalogue_pages": 3, "discovered": 60, "unique_urls": 60}
    assert len(targets) == 60
    assert run(fetcher=fake, output_dir=tmp_path) == 0
    first = json.loads((tmp_path / "books.json").read_text(encoding="utf-8"))
    assert len(first) == len({r["product_url"] for r in first}) == 60
    assert all(r["price_gbp"] == 12.5 for r in first)
    assert all("fetched_at" in r and "source_page" in r for r in first)
    assert run(fetcher=fake, output_dir=tmp_path) == 0
    again = json.loads((tmp_path / "books.json").read_text(encoding="utf-8"))
    assert first == again
    report = json.loads((tmp_path / "run-report.json").read_text())
    assert report["cache_hits"] >= 63
    assert report["valid_records"] == 60
    assert report["failed_pages"] == 0


def test_fake_404_does_not_kill_60_good_books(tmp_path):
    fake = FakeFetcher()
    assert run(include_broken=True, fetcher=fake, output_dir=tmp_path) == 0
    books = json.loads((tmp_path / "books.json").read_text())
    report = json.loads((tmp_path / "run-report.json").read_text())
    errors = json.loads((tmp_path / "errors.json").read_text())
    assert len(books) == 60
    assert report["unique_urls"] == 60 and report["attempted_detail_urls"] == 61
    assert report["invalid_records"] == 0 and report["failed_pages"] == 1
    assert errors[0]["stage"] == "fetch" and errors[0]["product_url"] == BROKEN_TEST_URL


def test_one_real_book_page_failure_causes_nonzero_exit(tmp_path):
    broken = PREFIX + "mock-book-10_1/index.html"
    fake = FakeFetcher(broken_book=broken)
    assert run(fetcher=fake, output_dir=tmp_path) == 1
    assert len(json.loads((tmp_path / "books.json").read_text())) == 59
    report = json.loads((tmp_path / "run-report.json").read_text())
    assert report["failed_pages"] == 1 and report["valid_records"] == 59


def test_missing_required_field_fails_validation():
    html = '<article class="product_page"><div class="product_main"><h1>X</h1></div></article>'
    with pytest.raises(ValueError, match="required"):
        extract_book(html, PREFIX + "a/index.html", START_URL, "2026-11-18T00:00:00Z")


def test_strict_price_validation():
    assert normalize_price("£1,234.50") == 1234.50
    for value in ("USD 42", "FREE", "£12.999", "no price", "£-1"):
        with pytest.raises(ValueError):
            normalize_price(value)


def test_exported_60_record_snapshot_is_valid_and_unique():
    path = Path(__file__).parents[1] / "output" / "books.json"
    books = json.loads(path.read_text(encoding="utf-8"))
    assert len(books) == len({x["product_url"] for x in books}) == 60
    for book in books:
        model = BookRecord.model_validate(book)
        assert str(model.product_url).startswith(PREFIX)
        assert model.price_gbp >= 0
        assert set(book) == set(type(model).model_fields)


def test_exfiltration_host_is_not_allowed(tmp_path):
    fetcher = PoliteFetcher(tmp_path, "Test-Agent", delay=0.5)
    for url in ("http://books.toscrape.com/", "https://evil.example/page",
                "https://books.toscrape.com.evil.example/", "file:///etc/passwd"):
        with pytest.raises(ValueError, match="Disallowed"):
            fetcher.get(url)
    assert fetcher.stats.pages_fetched == 0


class FakeResponse:
    def __init__(self, code, data="<html><body>£1.50</body></html>".encode("utf-8")):
        self.status_code = code
        self.content = data


def test_fetcher_decodes_utf8_and_reuses_cache(tmp_path):
    fetcher = PoliteFetcher(tmp_path, "Test-Agent", delay=0.5)
    calls = []
    fetcher.session.get = lambda *args, **kwargs: (calls.append((args, kwargs)) or FakeResponse(200))
    url = PREFIX + "book/index.html"
    html, status = fetcher.get(url)
    assert status == "FETCH" and "£1.50" in html
    assert calls[0][1]["timeout"] == 10 and calls[0][1]["allow_redirects"] is False
    assert fetcher.session.headers["User-Agent"] == "Test-Agent"
    html2, status2 = fetcher.get(url)
    assert status2 == "CACHE HIT" and html2 == html and len(calls) == 1


@pytest.mark.parametrize("code", [403, 404, 429])
def test_forbidden_not_retried(code, tmp_path):
    fetcher = PoliteFetcher(tmp_path, "Test-Agent")
    calls = []
    fetcher.session.get = lambda *args, **kwargs: (calls.append(1) or FakeResponse(code))
    with pytest.raises(RuntimeError, match=f"HTTP {code}"):
        fetcher.get(PREFIX + "x/index.html")
    assert len(calls) == 1


def test_http_500_one_retry(tmp_path, monkeypatch):
    monkeypatch.setattr("src.fetcher.time.sleep", lambda seconds: None)
    fetcher = PoliteFetcher(tmp_path, "Test-Agent")
    calls = []
    def get(*args, **kwargs):
        calls.append(1)
        return FakeResponse(500 if len(calls) == 1 else 200)
    fetcher.session.get = get
    html, marker = fetcher.get(PREFIX + "x/index.html")
    assert marker == "FETCH" and len(calls) == 2


def test_200_html_invalid_utf8_rejected(tmp_path):
    fetcher = PoliteFetcher(tmp_path, "Test-Agent")
    fetcher.session.get = lambda *args, **kwargs: FakeResponse(200, b"\xff")
    with pytest.raises(RuntimeError, match="UTF-8"):
        fetcher.get(PREFIX + "x/index.html")
