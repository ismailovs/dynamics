#!/usr/bin/env python3
"""
Asaxiy.uz product list scraper.

Strategy
--------
Phase 1 – Listing pages  (/product?page=N)
  Extracts from JSON-LD ItemList  : name, url, image, position
  Extracts from HTML card         : product_id, price, old_price,
                                    discount_badge, installment_months,
                                    installment_price, rating_count, star_count

Phase 2 – Detail pages  (/product/<slug>)
  Extracts from JSON-LD Product   : sku, mpn, gtin13, description, price,
                                    availability, condition, warranty_months,
                                    shipping_cost, rating_value, rating_count,
                                    reviews
  Extracts from HTML              : category_path (breadcrumbs), specs table
                                    (arbitrary key/value attributes)

Output
------
  scraper/products.jsonl  – one JSON object per line (full data)
  scraper/products.csv    – flat CSV (specs flattened as spec_<key> columns,
                            reviews serialised as JSON string)

Resume support: if products.jsonl already exists its URLs are skipped.
"""

import asyncio
import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

# ── configuration ─────────────────────────────────────────────────────────────
BASE_URL = "https://asaxiy.uz"
LISTING_URL = f"{BASE_URL}/product"
PRODUCTS_PER_PAGE = 24
MAX_CONCURRENCY = 12            # parallel fetches
REQUEST_DELAY = 0.2             # polite pause per worker (seconds)
RETRY_TIMES = 3
RETRY_DELAY = 5                 # seconds before retry
OUTPUT_DIR = Path(__file__).parent
JSONL_PATH = OUTPUT_DIR / "products.jsonl"
CSV_PATH = OUTPUT_DIR / "products.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "uz,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("asaxiy")


# ── helpers ────────────────────────────────────────────────────────────────────

def _clean_price(text: str) -> str:
    """Strip Uzbek currency label and whitespace, keep digits."""
    return re.sub(r"[^\d]", "", text) if text else ""


def extract_json_ld(html: str, target_type: str) -> dict | None:
    """Return first JSON-LD block whose @type matches target_type."""
    for block in re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    ):
        try:
            data = json.loads(block)
            if data.get("@type") == target_type:
                return data
        except json.JSONDecodeError:
            pass
    return None


def parse_listing_page(html: str) -> tuple[list[dict], int]:
    """
    Return (enriched-product-list, total_items).
    Each dict has at minimum: name, url, image, position.
    """
    # JSON-LD gives us the canonical list
    ld = extract_json_ld(html, "ItemList")
    if not ld:
        return [], 0

    ld_items: dict[str, dict] = {}
    for item in ld.get("itemListElement", []):
        url = item.get("url", "")
        if url:
            ld_items[url] = {
                "name": item.get("name", ""),
                "url": url,
                "image": item.get("image", ""),
                "position": item.get("position"),
            }

    total = int(ld.get("numberOfItems", 0))

    # HTML cards give us price, old price, product_id, rating, discount label
    soup = BeautifulSoup(html, "lxml")
    for card in soup.select(".product__item"):
        product_id = ""
        heart = card.select_one("[data-product-id]")
        if heart:
            product_id = heart.get("data-product-id", "")

        link = card.select_one("a[href^='/product/']")
        if not link:
            continue
        rel_url = link.get("href", "")
        full_url = BASE_URL + rel_url if rel_url.startswith("/") else rel_url

        entry = ld_items.get(full_url) or ld_items.get(rel_url) or {}

        # Price
        price_raw = card.get("data-actual-price", "")
        price = price_raw  # already digits-only from data attribute

        # Old / crossed-out price
        old_price_el = card.select_one(".product__item-old--price")
        old_price = _clean_price(old_price_el.get_text(strip=True)) if old_price_el else ""

        # Discount badge
        discount_badge = ""
        badge_el = card.select_one(".pr_discount, .pr_flash")
        if badge_el:
            discount_badge = badge_el.get_text(strip=True)

        # Installment info
        installment_months = card.get("data-installment-months", "")
        installment_price_el = card.select_one(".installment__price")
        installment_price_text = (
            installment_price_el.get_text(strip=True) if installment_price_el else ""
        )

        # Interest-free badge (e.g. "0-0-6")
        interest_free = ""
        if_el = card.select_one(".installment-interest-free")
        if if_el:
            interest_free = if_el.get_text(strip=True)

        # Rating count (e.g. "4 ta sharh")
        rating_text_el = card.select_one(".product__item-info--rating")
        rating_count_text = rating_text_el.get_text(strip=True) if rating_text_el else ""
        rating_count_num = ""
        m = re.search(r"(\d+)", rating_count_text)
        if m:
            rating_count_num = m.group(1)

        # Star count (filled stars)
        star_count = len(card.select(".fas.fa-star"))

        merged = {
            **entry,
            "url": full_url,          # always set; overrides possibly-missing entry url
            "product_id": product_id,
            "listing_price": price,
            "listing_old_price": old_price,
            "discount_badge": discount_badge,
            "installment_months": installment_months,
            "installment_price_text": installment_price_text,
            "interest_free_badge": interest_free,
            "listing_rating_count": rating_count_num,
            "listing_star_count": str(star_count) if star_count else "",
        }
        ld_items[full_url] = merged

    return list(ld_items.values()), total


def parse_detail_page(html: str, url: str) -> dict:
    """Extract all available fields from a product detail page."""
    product: dict[str, Any] = {"url": url}
    soup = BeautifulSoup(html, "lxml")

    # ── JSON-LD Product ──────────────────────────────────────────────────────
    ld = extract_json_ld(html, "Product")
    if ld:
        product["name"] = ld.get("name", "")
        product["sku"] = ld.get("sku", "")
        product["mpn"] = ld.get("mpn", "")
        product["gtin13"] = ld.get("gtin13", "")
        product["description"] = ld.get("description", "")
        product["image"] = ld.get("image", "")

        offers = ld.get("offers", {})
        product["price"] = offers.get("price", "")
        product["currency"] = offers.get("priceCurrency", "UZS")
        product["availability"] = (
            offers.get("availability", "").replace("https://schema.org/", "")
        )
        product["condition"] = (
            offers.get("itemCondition", "").replace("https://schema.org/", "")
        )
        warranty = offers.get("warranty", {}).get("durationOfWarranty", {})
        if warranty.get("unitCode") == "MON":
            product["warranty_months"] = warranty.get("value", "")
        shipping_rate = (
            offers.get("shippingDetails", {})
            .get("shippingRate", {})
            .get("value", "")
        )
        product["shipping_cost"] = shipping_rate

        rating = ld.get("aggregateRating", {})
        product["rating_value"] = rating.get("ratingValue", "")
        product["rating_count"] = rating.get("reviewCount", "")

        reviews = [
            {
                "author": r.get("author", {}).get("name", ""),
                "body": r.get("reviewBody", ""),
                "rating": r.get("reviewRating", {}).get("ratingValue", ""),
                "date": r.get("datePublished", ""),
            }
            for r in ld.get("review", [])
        ]
        product["reviews"] = reviews

    # ── Breadcrumbs → category path ──────────────────────────────────────────
    bc_links = soup.select("nav.breadcrumb a, .breadcrumb li a, .breadcrumb a")
    seen: list[str] = []
    for a in bc_links:
        text = a.get_text(strip=True)
        if text and text not in seen and text.lower() not in ("bosh sahifa", "home"):
            seen.append(text)
    # Last breadcrumb is the product name – remove it
    if seen and seen[-1] == product.get("name", "").strip():
        seen = seen[:-1]
    product["category_path"] = " > ".join(seen)

    # ── Original (crossed-out) price from HTML ───────────────────────────────
    for sel in (
        ".product__old-price",
        ".product-price__old",
        ".old-price",
        ".crossed-price",
        "del.price",
    ):
        el = soup.select_one(sel)
        if el:
            product["original_price_html"] = _clean_price(el.get_text(strip=True))
            break

    # ── Specs table ──────────────────────────────────────────────────────────
    specs: dict[str, str] = {}
    table = soup.find("table")
    if table:
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                val = cells[1].get_text(strip=True)
                if key:
                    specs[key] = val
    product["specs"] = specs

    return product


# ── async fetching ─────────────────────────────────────────────────────────────

async def fetch(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
) -> str | None:
    """Fetch URL with retries; return HTML text or None on failure."""
    async with semaphore:
        for attempt in range(1, RETRY_TIMES + 1):
            try:
                await asyncio.sleep(REQUEST_DELAY)
                async with session.get(
                    url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    if resp.status in (429, 503):
                        wait = RETRY_DELAY * attempt
                        log.warning(
                            "Rate limited (%s) on %s – waiting %ss",
                            resp.status, url, wait
                        )
                        await asyncio.sleep(wait)
                    else:
                        log.warning("HTTP %s for %s", resp.status, url)
                        return None
            except Exception as exc:
                log.warning("Error %s (attempt %d): %s", url, attempt, exc)
                await asyncio.sleep(RETRY_DELAY * attempt)
    return None


# ── phase 1 ───────────────────────────────────────────────────────────────────

async def scrape_listing_pages(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Collect basic product info from all listing pages."""
    log.info("Fetching page 1 to discover product count…")
    html1 = await fetch(session, LISTING_URL, semaphore)
    if not html1:
        log.error("Could not fetch listing page 1 – aborting.")
        sys.exit(1)

    basics, total = parse_listing_page(html1)
    total_pages = (total + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    log.info("Total products: %d  |  Pages: %d", total, total_pages)

    all_basics = list(basics)

    async def fetch_listing(page_url: str) -> list[dict]:
        html = await fetch(session, page_url, semaphore)
        return parse_listing_page(html)[0] if html else []

    remaining = [f"{LISTING_URL}?page={p}" for p in range(2, total_pages + 1)]
    batch_size = MAX_CONCURRENCY * 4

    for i in range(0, len(remaining), batch_size):
        batch = remaining[i : i + batch_size]
        results = await asyncio.gather(*[fetch_listing(u) for u in batch])
        for r in results:
            all_basics.extend(r)
        done = i + len(batch) + 1
        log.info(
            "Listing pages: %d / %d  (products so far: %d)",
            done, total_pages, len(all_basics),
        )

    log.info("Phase 1 complete – %d product URLs collected.", len(all_basics))
    return all_basics


# ── phase 2 ───────────────────────────────────────────────────────────────────

_CSV_BASE_FIELDS = [
    "url", "product_id", "name", "sku", "mpn", "gtin13", "description", "image",
    "category_path",
    "price", "currency", "listing_price", "listing_old_price", "original_price_html",
    "availability", "condition",
    "discount_badge", "interest_free_badge",
    "installment_months", "installment_price_text",
    "warranty_months", "shipping_cost",
    "rating_value", "rating_count", "listing_rating_count", "listing_star_count",
    "position", "reviews_json",
]


def _flatten(product: dict, csv_fieldnames: list[str]) -> dict:
    """Flatten specs into spec_* columns; serialise reviews."""
    specs = product.pop("specs", {}) or {}
    reviews = product.pop("reviews", []) or []
    row: dict[str, Any] = dict(product)
    for k, v in specs.items():
        col = f"spec_{k}"
        row[col] = v
        if col not in csv_fieldnames:
            csv_fieldnames.append(col)
    row["reviews_json"] = json.dumps(reviews, ensure_ascii=False) if reviews else ""
    for fn in csv_fieldnames:
        row.setdefault(fn, "")
    return row


async def scrape_detail_pages(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    basics: list[dict],
    jsonl_out,
    csv_writer_ref: list,       # mutable container so we can replace writer
    csv_fieldnames: list[str],
    already_done: set[str],
    csv_path: Path,
) -> int:
    """Phase 2: enrich every product with detail-page data."""
    todo = [b for b in basics if b.get("url") and b["url"] not in already_done]
    log.info("Phase 2: %d products to fetch (skipping %d already done)",
             len(todo), len(already_done))

    done_count = 0

    async def process_one(basic: dict) -> dict | None:
        url = basic["url"]
        html = await fetch(session, url, semaphore)
        if not html:
            return {**basic}
        detail = parse_detail_page(html, url)
        return {**basic, **detail}

    batch_size = MAX_CONCURRENCY

    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]
        results = await asyncio.gather(*[process_one(b) for b in batch])

        for product in results:
            if product is None:
                continue
            # ---- JSONL ----
            jsonl_out.write(json.dumps(product, ensure_ascii=False) + "\n")
            jsonl_out.flush()
            # ---- CSV ----
            row = _flatten(dict(product), csv_fieldnames)
            csv_writer_ref[0].writerow(row)
            done_count += 1

        if (i + batch_size) % 200 == 0 or (i + batch_size) >= len(todo):
            log.info(
                "Detail pages: %d / %d  (total written: %d)",
                min(i + batch_size, len(todo)), len(todo), done_count,
            )

    return done_count


# ── entry point ────────────────────────────────────────────────────────────────

async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Resume support
    already_done: set[str] = set()
    if JSONL_PATH.exists():
        with open(JSONL_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get("url"):
                        already_done.add(obj["url"])
                except Exception:
                    pass
        log.info("Resuming – %d products already in output.", len(already_done))

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENCY, ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        basics = await scrape_listing_pages(session, semaphore)

        csv_fieldnames = list(_CSV_BASE_FIELDS)
        mode = "a" if already_done else "w"

        with (
            open(JSONL_PATH, mode, encoding="utf-8") as jsonl_out,
            open(CSV_PATH, mode, encoding="utf-8", newline="") as csv_out,
        ):
            writer = csv.DictWriter(
                csv_out, fieldnames=csv_fieldnames, extrasaction="ignore"
            )
            if mode == "w":
                writer.writeheader()
            writer_ref = [writer]

            count = await scrape_detail_pages(
                session, semaphore, basics, jsonl_out,
                writer_ref, csv_fieldnames, already_done, CSV_PATH,
            )

    log.info("Done! %d products written to:", count)
    log.info("  %s", JSONL_PATH)
    log.info("  %s", CSV_PATH)


if __name__ == "__main__":
    asyncio.run(main())
