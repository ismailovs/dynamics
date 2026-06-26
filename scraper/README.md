# book.uz scraper

Scrapes the full book catalogue from [book.uz](https://book.uz) — an Uzbek online bookstore — using its undocumented but publicly accessible REST API.

## What it collects

Each book record includes:

| Field | Notes |
|---|---|
| `id` | MongoDB object ID |
| `name` | Book title |
| `link` | URL slug |
| `author_id` / `author_name` | Only populated when `--enrich` is used |
| `publisher` | Only populated when `--enrich` is used |
| `translator` | Translator name (if any) |
| `year` | Publication year |
| `language` | Book language code (`uz`, `ru`, `en`, …) |
| `content_language` | Script (`latin`, `cyrillic`) |
| `cover` | Binding type (`paper`, `hardcover`, `integral`) |
| `paper_format` | Page size (e.g. `A5`) |
| `number_of_pages` | |
| `barcode` | ISBN / barcode |
| `book_price_uzs` | Physical book price (Uzbek Sum) |
| `ebook_price_uzs` | E-book price |
| `audio_price_uzs` | Audiobook price |
| `has_discount` / `discount_pct` | Current discounts |
| `rating` / `rate_count` | Average rating and number of ratings |
| `views_count` | Page views |
| `amount_in_stock` | Current stock count |
| `total_sold` | Total units sold |
| `is_available` | Whether the book can be ordered |
| `is_available_ebook` / `is_available_audio` / `is_available_podcast` | |
| `label` | Book label (`simple`, `new`, …) |
| `state` | Record state |
| `type` | Book type (`single`, `series`, …) |
| `genres` | Semicolon-separated genre names |
| `tags` | Semicolon-separated search tags |
| `img_url` | Cover image path (prepend `https://book.uz/` to get the full URL) |
| `description` | Plain-text book description |

The catalogue contained **~6 700 books** at the time of writing.

## Requirements

Python 3.9+ — no third-party packages needed (uses `urllib` from the standard library).

## Usage

```bash
# Scrape everything (JSON + CSV)
python3 bookuz_scraper.py

# Limit to the 200 most recent books
python3 bookuz_scraper.py --limit 200

# Scrape 500 books and also enrich each record with author/publisher details
# (makes one extra HTTP request per book — takes longer)
python3 bookuz_scraper.py --limit 500 --enrich

# CSV only, custom output directory
python3 bookuz_scraper.py --format csv --out-dir /tmp/bookuz

# All options
python3 bookuz_scraper.py --help
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--limit N` | all | Maximum number of books to fetch |
| `--page-size N` | 100 | Books per API request |
| `--out-dir DIR` | `./output` | Directory for output files |
| `--format json\|csv\|both` | `both` | Output format(s) |
| `--enrich` | off | Fetch per-book detail to populate `author_name`, `publisher` |

## Output files

Three timestamped files are written to `--out-dir`:

| File | Format | Contents |
|---|---|---|
| `bookuz_raw_<stamp>.json` | JSON array | Raw API records (unmodified) |
| `bookuz_flat_<stamp>.json` | JSON array | Flattened / normalised records |
| `bookuz_<stamp>.csv` | CSV | Flattened records, UTF-8 with BOM |

## Notes

- The scraper adds a short delay between requests to avoid overwhelming the server.
- Author data is **not** included in the paginated list API — it requires the `--enrich` flag.
- Image URLs are relative; prepend `https://book.uz/` to build the full URL.
- Prices are in **UZS** (Uzbek Sum). At time of writing 1 USD ≈ 12 800 UZS.
