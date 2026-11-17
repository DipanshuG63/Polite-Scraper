from pathlib import Path
from src.parser import absolute_url, extract_book, normalize_price, extract_catalogue_links

FIXTURE = Path(__file__).parent / "fixtures" / "book.html"


def test_price_normalization():
    assert normalize_price("£1,234.50") == 1234.50


def test_relative_url():
    assert absolute_url("../book/example_1/index.html", "https://books.toscrape.com/catalogue/page-1.html") == "https://books.toscrape.com/book/example_1/index.html"


def test_missing_description_is_none():
    html = '''<html><body><article class="product_page"><div class="product_main"><h1>A Fixture Book</h1><p class="price_color">£12.50</p><p class="instock availability">In stock</p><p class="star-rating Three">Rating</p></div></article></body></html>'''
    record = extract_book(html, "https://books.toscrape.com/catalogue/example_1/index.html", "https://books.toscrape.com/catalogue/page-1.html", "2026-10-07T00:00:00+00:00")
    assert record["description"] is None


def test_duplicate_urls_removed():
    html = '''<html><body><article class="product_pod"><h3><a href="../book/a/index.html">A</a></h3></article><article class="product_pod"><h3><a href="../book/a/index.html">A again</a></h3></article></body></html>'''
    links, _ = extract_catalogue_links(html, "https://books.toscrape.com/catalogue/page-1.html")
    assert links.count("https://books.toscrape.com/book/a/index.html") == 2
    assert list(dict.fromkeys(links)) == ["https://books.toscrape.com/book/a/index.html"]


def test_malformed_fixture_fails():
    bad = "<html><body><h1>Not a product page</h1></body></html>"
    try:
        extract_book(bad, "https://example.com/book", "https://example.com/page-1", "2026-10-07T00:00:00+00:00")
    except ValueError as exc:
        assert "product area" in str(exc)
    else:
        raise AssertionError("malformed fixture should fail")
