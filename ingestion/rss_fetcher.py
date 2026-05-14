"""
RSS Ingester
------------
Fetches all configured RSS feeds, dedupes on URL, and inserts new items
into the raw_items table.

Run standalone:
    python -m ingestion.rss_fetcher
"""

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import psycopg2

from config.feeds import RSS_FEEDS
from db.connection import get_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)


def _parse_date(entry) -> datetime | None:
    """Extract a timezone-aware datetime from an RSS entry. Returns None if unavailable."""
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    # feedparser also parses into a struct_time under published_parsed
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        import calendar
        ts = calendar.timegm(entry.published_parsed)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    return None


def _clean(text: str | None) -> str | None:
    """Strip HTML tags from body text."""
    if not text:
        return None
    import re
    return re.sub(r"<[^>]+>", "", text).strip() or None


def fetch_feed(feed_cfg: dict) -> list[dict]:
    """Parse a single RSS feed and return a list of item dicts."""
    source = feed_cfg["source"]
    url = feed_cfg["url"]
    log.info("Fetching %-28s  %s", source, url)

    parsed = feedparser.parse(url)

    if parsed.bozo:
        log.warning("Feed parse warning for %s: %s", source, parsed.bozo_exception)

    items = []
    for entry in parsed.entries:
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue

        body = _clean(
            getattr(entry, "summary", None)
            or getattr(entry, "description", None)
        )

        items.append({
            "source": source,
            "url": link,
            "title": title.strip(),
            "body": body,
            "published_at": _parse_date(entry),
        })

    log.info("  → %d items from %s", len(items), source)
    return items


def save_items(items: list[dict]) -> int:
    """
    Bulk-insert items, ignoring duplicates (ON CONFLICT DO NOTHING on url).
    Returns the number of newly inserted rows.
    """
    if not items:
        return 0

    inserted = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for item in items:
                try:
                    cur.execute(
                        """
                        INSERT INTO raw_items (source, url, title, body, published_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (url) DO NOTHING
                        """,
                        (
                            item["source"],
                            item["url"],
                            item["title"],
                            item["body"],
                            item["published_at"],
                        ),
                    )
                    if cur.rowcount:
                        inserted += 1
                except psycopg2.Error as e:
                    log.error("DB error inserting %s: %s", item["url"], e)
    return inserted


def run_all() -> None:
    """Fetch all configured feeds and persist new items."""
    total_new = 0
    for feed_cfg in RSS_FEEDS:
        items = fetch_feed(feed_cfg)
        new = save_items(items)
        log.info("  → %d new items saved from %s", new, feed_cfg["source"])
        total_new += new
    log.info("Ingestion complete. Total new items: %d", total_new)


if __name__ == "__main__":
    run_all()
