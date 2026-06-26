#!/usr/bin/env python3
"""
book.uz scraper
Fetches all books from the book.uz public API and saves to JSON and CSV.

Usage:
    python3 bookuz_scraper.py [--limit N] [--out-dir DIR] [--format json|csv|both]

The scraper uses the undocumented but publicly accessible REST API at:
    https://backend.book.uz/user-api/book?page=<N>&limit=<N>
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import urllib.request
    import urllib.error
    import urllib.parse
except ImportError:
    sys.exit("Python 3.x is required")

BASE_URL = "https://backend.book.uz/user-api"
BOOKS_ENDPOINT = "/book"
DEFAULT_PAGE_SIZE = 100
REQUEST_DELAY = 0.3   # seconds between paginated requests
ENRICH_DELAY  = 0.15  # seconds between individual detail requests


def fetch_json(url: str, retries: int = 3, backoff: float = 2.0) -> dict:
    """Fetch a URL and return parsed JSON, with retry logic."""
    headers = {
        "Accept": "application/json",
        "language": "uz",
        "User-Agent": "bookuz-scraper/1.0 (educational purposes)",
    }
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if attempt == retries:
                raise
            wait = backoff ** attempt
            print(f"  HTTP {exc.code} on attempt {attempt}, retrying in {wait:.0f}s…", file=sys.stderr)
            time.sleep(wait)
        except (urllib.error.URLError, OSError) as exc:
            if attempt == retries:
                raise
            wait = backoff ** attempt
            print(f"  Network error on attempt {attempt}: {exc}, retrying in {wait:.0f}s…", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


def extract_text(field) -> str:
    """Flatten a description field (list of text blocks or plain string)."""
    if isinstance(field, str):
        return field.strip()
    if isinstance(field, list):
        return " ".join(
            block.get("value", "") for block in field if isinstance(block, dict)
        ).strip()
    return ""


def flatten_book(book: dict) -> dict:
    """Flatten a raw API book record into a simple dict."""
    author = book.get("author") or {}
    if isinstance(author, list):
        author_name = "; ".join(a.get("fullName", "") for a in author if isinstance(a, dict))
        author_id = "; ".join(a.get("_id", "") for a in author if isinstance(a, dict))
    elif isinstance(author, dict):
        author_name = author.get("fullName", "")
        author_id = author.get("_id", "")
    elif author:
        author_name = str(author)
        author_id = ""
    else:
        author_name = ""
        author_id = ""

    publisher = book.get("publisher") or {}
    publisher_name = publisher.get("name", "") if isinstance(publisher, dict) else str(publisher or "")

    genres = book.get("genres") or []
    genre_names = "; ".join(g.get("name", "") for g in genres if isinstance(g, dict))

    tags = book.get("tags") or []
    tags_str = "; ".join(str(t) for t in tags)

    discounts = book.get("discounts") or []
    discount_pct = ""
    if discounts:
        pcts = [str(d.get("discountPercent", "")) for d in discounts if isinstance(d, dict)]
        discount_pct = "; ".join(pcts)

    description = extract_text(book.get("description", ""))

    return {
        "id": book.get("_id", ""),
        "name": book.get("name", ""),
        "link": book.get("link", ""),
        "author_id": author_id,
        "author_name": author_name,
        "publisher": publisher_name,
        "translator": book.get("translator") or "",
        "year": book.get("year", ""),
        "language": book.get("language", ""),
        "content_language": book.get("contentLanguage", ""),
        "cover": book.get("cover", ""),
        "paper_format": book.get("paperFormat", ""),
        "number_of_pages": book.get("numberOfPage", ""),
        "weight": book.get("weight", ""),
        "barcode": book.get("barcode", ""),
        "book_price_uzs": book.get("bookPrice", ""),
        "ebook_price_uzs": book.get("ebookPrice", ""),
        "audio_price_uzs": book.get("audioPrice", ""),
        "has_discount": book.get("hasDiscount", False),
        "discount_pct": discount_pct,
        "rating": book.get("rating", ""),
        "rate_count": book.get("rateCount", ""),
        "views_count": book.get("viewsCount", ""),
        "amount_in_stock": book.get("amount") if book.get("amount") is not None else book.get("stockCount", ""),
        "total_sold": book.get("totalSold", book.get("soldBookCount", "")),
        "is_available": book.get("isAvailable", ""),
        "is_available_ebook": book.get("isAvailableEbook", ""),
        "is_available_audio": book.get("isAvailableAudio", ""),
        "is_available_podcast": book.get("isAvailablePotcast", ""),
        "label": book.get("label", ""),
        "state": book.get("state", ""),
        "type": book.get("type", ""),
        "genres": genre_names,
        "tags": tags_str,
        "img_url": book.get("imgUrl", ""),
        "description": description,
    }


def enrich_book(book: dict) -> dict:
    """Fetch the individual detail record and merge author/publisher into the book dict."""
    book_id = book.get("_id", "")
    if not book_id:
        return book
    try:
        url = f"{BASE_URL}{BOOKS_ENDPOINT}/{book_id}"
        detail = fetch_json(url)
        if detail.get("success") is False:
            return book
        d = detail.get("data", {})
        for key in ("author", "publisher"):
            if d.get(key):
                book[key] = d[key]
    except Exception:
        pass
    return book


def scrape_books(max_books: int | None = None, page_size: int = DEFAULT_PAGE_SIZE,
                 enrich: bool = False) -> list[dict]:
    """Fetch all books from the API, returning a list of raw records."""
    # First call to get total count
    first_page_url = f"{BASE_URL}{BOOKS_ENDPOINT}?page=1&limit=1"
    first = fetch_json(first_page_url)
    total = first["data"]["total"]
    if max_books:
        total = min(total, max_books)

    print(f"Total books available: {first['data']['total']:,}  "
          f"(scraping up to {total:,})")

    books: list[dict] = []
    page = 1
    while len(books) < total:
        limit = min(page_size, total - len(books))
        url = f"{BASE_URL}{BOOKS_ENDPOINT}?page={page}&limit={limit}"
        data = fetch_json(url)
        batch = data["data"]["data"]
        if not batch:
            break
        books.extend(batch)
        pct = 100 * len(books) / total
        print(f"  Page {page:>4}: fetched {len(batch):>4} books  "
              f"[{len(books):>6}/{total:>6}  {pct:5.1f}%]")
        page += 1
        if len(books) < total:
            time.sleep(REQUEST_DELAY)

    if enrich:
        print(f"\nEnriching {len(books):,} books with author/publisher details…")
        for idx, book in enumerate(books, 1):
            books[idx - 1] = enrich_book(book)
            if idx % 50 == 0 or idx == len(books):
                pct = 100 * idx / len(books)
                print(f"  Enriched {idx:>6}/{len(books):>6}  {pct:5.1f}%")
            time.sleep(ENRICH_DELAY)

    return books


def save_json(books: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(books, fh, ensure_ascii=False, indent=2)
    print(f"Saved JSON  → {path}  ({path.stat().st_size / 1024:.1f} KB)")


def save_csv(flat_books: list[dict], path: Path) -> None:
    if not flat_books:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(flat_books[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_books)
    print(f"Saved CSV   → {path}  ({path.stat().st_size / 1024:.1f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape all books from book.uz and save to JSON/CSV."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max number of books to fetch (default: all)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        metavar="N",
        help=f"Books per API request (default: {DEFAULT_PAGE_SIZE})",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="output",
        metavar="DIR",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        default=False,
        help=(
            "Fetch individual book details to include author/publisher "
            "(makes one extra request per book — slow for large datasets)"
        ),
    )
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)

    print("=" * 60)
    print("book.uz scraper")
    print(f"  API base : {BASE_URL}")
    print(f"  Page size: {args.page_size}")
    print(f"  Limit    : {args.limit or 'all'}")
    print(f"  Format   : {args.format}")
    print(f"  Enrich   : {args.enrich}")
    print(f"  Output   : {out_dir.resolve()}")
    print("=" * 60)

    t0 = time.monotonic()
    raw_books = scrape_books(max_books=args.limit, page_size=args.page_size,
                             enrich=args.enrich)
    elapsed = time.monotonic() - t0

    print(f"\nFetched {len(raw_books):,} books in {elapsed:.1f}s")

    flat_books = [flatten_book(b) for b in raw_books]

    if args.format in ("json", "both"):
        save_json(raw_books, out_dir / f"bookuz_raw_{stamp}.json")
        save_json(flat_books, out_dir / f"bookuz_flat_{stamp}.json")

    if args.format in ("csv", "both"):
        save_csv(flat_books, out_dir / f"bookuz_{stamp}.csv")

    # Quick statistics
    prices = [b["book_price_uzs"] for b in flat_books if isinstance(b["book_price_uzs"], (int, float)) and b["book_price_uzs"] > 0]
    if prices:
        avg_price = sum(prices) / len(prices)
        print(f"\nQuick stats:")
        print(f"  Books with price data : {len(prices):,}")
        print(f"  Avg price (UZS)       : {avg_price:,.0f}")
        print(f"  Min price (UZS)       : {min(prices):,}")
        print(f"  Max price (UZS)       : {max(prices):,}")

    langs = {}
    for b in flat_books:
        lang = b.get("language") or "unknown"
        langs[lang] = langs.get(lang, 0) + 1
    if langs:
        print(f"  Languages             : {dict(sorted(langs.items(), key=lambda x: -x[1]))}")

    print("\nDone.")


if __name__ == "__main__":
    main()
