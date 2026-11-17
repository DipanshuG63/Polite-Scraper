"""Strict HTML extraction and normalization for Books to Scrape only."""
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def normalize_price(price_text: str) -> float:
    cleaned = price_text.strip().replace(",", "").replace("Â£", "£")
    if not re.fullmatch(r"£\s*\d+(?:\.\d{1,2})?", cleaned):
        raise ValueError(f"invalid GBP price: {price_text!r}")
    return float(cleaned.replace("£", "").strip())


def absolute_url(href: str, base_url: str) -> str:
    return urljoin(base_url, href)


def extract_catalogue_links(html: str, page_url: str) -> tuple[list[str], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    links = [absolute_url(a["href"], page_url)
             for a in soup.select("article.product_pod h3 a[href]")]
    next_link = soup.select_one("li.next a[href]")
    next_url = absolute_url(next_link["href"], page_url) if next_link else None
    return links, next_url


def extract_book(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("article.product_page")
    if product is None:
        raise ValueError("product area not found")

    title = product.select_one("div.product_main h1")
    price = product.select_one("div.product_main p.price_color")
    stock = product.select_one("div.product_main p.instock.availability")
    rating = product.select_one("div.product_main p.star-rating")
    description = product.select_one("div#product_description + p")
    if any(node is None for node in (title, price, stock, rating)):
        raise ValueError("one or more required product fields are missing")

    rating_text = next((name for name in RATING_MAP if name in rating.get("class", [])), "")
    if not rating_text:
        raise ValueError("rating value missing")

    price_text = price.get_text(" ", strip=True)
    return {
        "title": title.get_text(" ", strip=True),
        "product_url": product_url,
        "price_text": price_text,
        "price_gbp": normalize_price(price_text),
        "availability_text": stock.get_text(" ", strip=True),
        "rating_text": rating_text,
        "description": description.get_text(" ", strip=True) if description else None,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
