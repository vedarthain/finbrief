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


# ── Fluff filter — drop lifestyle / opinion / clickbait at ingestion ─────────
# Matched against lowercased title. If ANY pattern matches, the item is skipped.
import re as _re
_FLUFF_PATTERNS = [
    # First-person opinion / personal-finance fluff
    _re.compile(r"\bi['’]m\s+\d{2}\b"),                  # "I'm 75..."
    _re.compile(r"\bi['’]ve\s+(?:got|saved|made|been)"), # "I've saved..."
    _re.compile(r"\bi\s+(?:have|live|earn|spend|retired|inherited)\b"),
    _re.compile(r"\bmy\s+(?:wife|husband|son|daughter|partner|mom|dad|kid|spouse|boyfriend|girlfriend)\b"),
    _re.compile(r"\b(?:should|can|do|will)\s+i\s+\w+\?"),
    _re.compile(r"\bzero\s+envy\b"),
    _re.compile(r"\bwhy\s+(?:are|is|do)\s+more\s+people\s+not\b"),

    # Lifestyle / horoscope / gossip
    _re.compile(r"\b(horoscope|zodiac|astrology|tarot|numerology|vastu)\b"),
    _re.compile(r"\b(recipe|cooking|kitchen|cuisine|food review|street food)\b"),
    _re.compile(r"\b(celebrity|gossip|bollywood|hollywood|tollywood|kollywood)\b"),
    _re.compile(r"\b(netflix series|movie review|film review|web series|ott series)\b"),
    _re.compile(r"\b(travel diary|trip report|vacation|holiday destination)\b"),
    _re.compile(r"\b(weight loss|skincare|fashion|workout|fitness tips|beauty tips)\b"),
    _re.compile(r"\b(diet plan|yoga|meditation|wellness routine)\b"),

    # Sports
    _re.compile(r"\b(cricket|cricketer|cricketers|football|footballer|tennis|olympics|fifa|ipl|world cup|t20|odi|test match)\b"),
    _re.compile(r"\b(virat|rohit|dhoni|messi|ronaldo|kohli|rayudu|mcclenaghan|gambhir|ashwin|jadeja|sehwag|gavaskar)\b"),
    _re.compile(r"\b(batsman|bowler|wicket|innings|runs scored|over rate|all[\s-]?rounder)\b"),
    _re.compile(r"\b(bcci|icc cricket|test series|odi series|t20 series|asia cup)\b"),

    # Crime / accidents / personal tragedy — not financial news
    _re.compile(r"\b(rape|raped|gang-rape|gang rape|molested|molestation|sexual assault)\b"),
    _re.compile(r"\b(murder|murdered|killed|shot dead|stabbed|hacked to death)\b"),
    _re.compile(r"\b(suicide|self-immolation|hangs himself|hangs herself)\b"),
    _re.compile(r"\b(postmortem|autopsy|cardiorespiratory|hospitalised)\b"),
    _re.compile(r"\b(arrested|arrest|nabbed|held by police|in police custody)\b"),
    _re.compile(r"\b(accident|accidents|car crash|road mishap|train collision|plane crash)\b"),
    _re.compile(r"\b(dies|died|passes away|passed away|no more)\b"),
    _re.compile(r"\b(fire breaks out|massive fire|building collapse|fatal fire)\b"),
    _re.compile(r"\b(kidnap|kidnapped|abducted)\b"),

    # Politics / elections fluff (keep pure policy/budget — those mention "policy", "budget", "rbi")
    _re.compile(r"\bbypoll|by-election|by election\b"),
    _re.compile(r"\b(rally|roadshow|campaign trail|election commission)\b"),

    # Personal-life / opinion columns
    _re.compile(r"^\d+\s+(?:things|ways|reasons|tips|signs|habits|mistakes)\b"),
    _re.compile(r"\bhere['’]s\s+(?:how|why|what)\s+i\b"),
    _re.compile(r"\bdear\s+(?:moneyist|abby|reader)\b"),
    _re.compile(r"\b(love advice|marriage advice|relationship advice)\b"),

    # Weather / natural events (only relevant when economy-impacting like cyclone)
    _re.compile(r"\b(weather forecast|imd predicts|temperature soars)\b"),

    # Education / exam / admit-card / recruitment fluff
    _re.compile(r"\b(admit card|hall ticket|answer key|result declared|cut[\s-]?off|merit list)\b"),
    _re.compile(r"\b(neet|jee|upsc|ssc|cuet|cat exam|gate exam|tet|ctet|bstc|d\.?el\.?ed|b\.?ed)\b"),
    _re.compile(r"\b(class 10|class 12|board exam|board result|cbse result|icse result)\b"),
    _re.compile(r"\b(university admission|college admission|counselling schedule)\b"),
    _re.compile(r"\b(railway recruitment|bank po recruitment|teacher recruitment|constable recruitment)\b"),
    _re.compile(r"\b(scholarship application|fellowship application)\b"),

    # Astro / spiritual / temple
    _re.compile(r"\b(temple|puja|aarti|spiritual|guru|swami|baba)\b"),

    # Viral / human-interest
    _re.compile(r"\b(goes viral|viral video|viral photo|netizens|trolled|trolls)\b"),
    _re.compile(r"\b(watch:|video:|pics:|in pics|in pictures)\b", _re.IGNORECASE),
    _re.compile(r"\b(uber ceo takes|man dies|woman dies|teen dies|child dies)\b"),

    # Broker calls / stock picks / tip-sheet content
    # These are recommendation columns, not real news. Pattern to keep:
    # "X shares fall as Goldman cuts target" → KEEP (price reaction to analyst action)
    # "Brokerages recommend X, Y, Z" → DROP (just tip sheet)
    _re.compile(r"\b(stocks? to buy|stocks? to sell|stock picks?|stock ideas?)\b"),
    # Only treat "top N stocks" as a pick if followed by "to buy/sell" or as a header phrase.
    # "DII buying ... top 10 stocks" is real news — must NOT match here.
    _re.compile(r"\btop \d+ stocks? to (buy|sell|invest|watch today)\b"),
    _re.compile(r"\btop stock (picks?|ideas?|bets?|recommendations?)\b"),
    _re.compile(r"\brecommended? for gains? (of|up to)\b"),
    _re.compile(r"\brecommend(?:s|ed)? (?:[a-z][a-z\s,&\-]+){1,5} (?:buy|shares?|stocks?)\b"),
    _re.compile(r"\b(brokerages?|brokerage firms?) (?:recommend|pick|suggest|favou?r)\b"),
    _re.compile(r"\b(buy|sell|hold) (?:call|rating|recommendation)s?\b"),
    _re.compile(r"\b(intraday|day[\s-]?trading) (?:tips?|picks?|recommendations?|calls?)\b"),
    _re.compile(r"\b(f&o|futures?\s+and\s+options) (?:picks?|tips?|strategy|strategies)\b"),
    _re.compile(r"\bshares? for (?:short[\s-]?term|long[\s-]?term|intraday)\b"),
    _re.compile(r"\bmarket analysts? (?:issue|recommend|suggest)\b"),
    _re.compile(r"\b(?:axis|kotak|motilal|icici|hdfc|sharekhan|emkay|nuvama|jefferies)\s+(?:securities|institutional|direct)?\s*recommends?\b", _re.IGNORECASE),
    _re.compile(r"\bnagaraj shetti|raja venkatraman|amol athawale|marketsmith\b", _re.IGNORECASE),
    _re.compile(r"\bbuy [a-z][a-z\s,&\-]+ for (?:up to )?\d+(?:\.\d+)?%", _re.IGNORECASE),
    # Headlines starting with "Buy <Stock>" or "Sell <Stock>" are recommendations
    _re.compile(r"^(buy|sell)\s+[A-Z]", _re.IGNORECASE),
    _re.compile(r"\b(?:trading|investment) calls? for\b"),
    _re.compile(r"\btarget price (?:of )?₹|target ₹\d"),
]


def is_fluff(title: str) -> bool:
    """Return True if title looks like lifestyle/opinion/clickbait rather than financial news."""
    if not title:
        return True
    t = title.lower()
    return any(p.search(t) for p in _FLUFF_PATTERNS)


def fetch_feed(feed_cfg: dict) -> list[dict]:
    """Parse a single RSS feed and return a list of item dicts."""
    source = feed_cfg["source"]
    url = feed_cfg["url"]
    log.info("Fetching %-28s  %s", source, url)

    parsed = feedparser.parse(url)

    if parsed.bozo:
        log.warning("Feed parse warning for %s: %s", source, parsed.bozo_exception)

    items = []
    skipped_fluff = 0
    for entry in parsed.entries:
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue

        title = title.strip()
        if is_fluff(title):
            skipped_fluff += 1
            continue

        body = _clean(
            getattr(entry, "summary", None)
            or getattr(entry, "description", None)
        )

        items.append({
            "source": source,
            "url": link,
            "title": title,
            "body": body,
            "published_at": _parse_date(entry),
        })

    if skipped_fluff:
        log.info("  → %d items from %s (skipped %d fluff)", len(items), source, skipped_fluff)
    else:
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
