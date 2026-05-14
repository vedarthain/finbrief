"""
Price Fetcher
-------------
Pulls current prices for all WATCHLIST_TICKERS using yfinance and
persists them to the prices table.

Handles:
- Indices (^NSEI, ^BSESN)
- NSE stocks (RELIANCE.NS)
- Forex pairs (USDINR=X)
- Commodities (CL=F, GC=F)

Run standalone:
    python -m ingestion.price_fetcher
"""

import json
import logging
import urllib.request
from datetime import datetime, timezone

import yfinance as yf

from config.feeds import WATCHLIST_TICKERS
from db.connection import get_conn


def _yahoo_v8_latest(ticker: str) -> dict | None:
    """Fallback: fetch the latest day's OHLC from Yahoo's v8 chart endpoint."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        result = (data.get("chart", {}).get("result") or [None])[0]
        if not result:
            return None
        meta = result.get("meta", {})
        q = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes = [c for c in (q.get("close") or []) if c is not None]
        if not closes:
            return None
        opens   = [c for c in (q.get("open") or []) if c is not None]
        highs   = [c for c in (q.get("high") or []) if c is not None]
        lows    = [c for c in (q.get("low") or []) if c is not None]
        volumes = [c for c in (q.get("volume") or []) if c is not None]
        return {
            "price":  float(meta.get("regularMarketPrice", closes[-1])),
            "open":   float(opens[-1])   if opens   else None,
            "high":   float(highs[-1])   if highs   else None,
            "low":    float(lows[-1])    if lows    else None,
            "volume": int(volumes[-1])   if volumes else 0,
        }
    except Exception:
        return None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)


def fetch_prices(tickers: dict[str, str] | None = None) -> list[dict]:
    """
    Fetch latest price for each ticker in WATCHLIST_TICKERS (or a supplied dict).
    Uses yf.Ticker per symbol — more reliable across yfinance versions.
    Returns a list of price dicts ready to insert.
    """
    tickers = tickers or WATCHLIST_TICKERS
    symbols = list(tickers.keys())

    log.info("Fetching prices for %d tickers …", len(symbols))

    results = []
    now = datetime.now(tz=timezone.utc)

    for symbol in symbols:
        try:
            ticker_obj = yf.Ticker(symbol)
            # fast_info is the lightest call — single HTTP request per ticker
            info = ticker_obj.fast_info

            price = getattr(info, "last_price", None)
            open_ = getattr(info, "open", None)
            high  = getattr(info, "day_high", None)
            low   = getattr(info, "day_low", None)

            if price is None:
                # yfinance gave up — try Yahoo v8 direct
                fb = _yahoo_v8_latest(symbol)
                if fb:
                    price, open_, high, low = fb["price"], fb["open"], fb["high"], fb["low"]
                    results.append({
                        "ticker":      symbol,
                        "price":       round(price, 4),
                        "open":        round(open_, 4) if open_ else None,
                        "high":        round(high, 4)  if high  else None,
                        "low":         round(low, 4)   if low   else None,
                        "volume":      fb["volume"],
                        "recorded_at": now,
                    })
                    log.info("  %-18s  %.4f  (v8 fallback)", symbol, price)
                    continue
                log.warning("No price data for %s", symbol)
                continue

            # volume is not always in fast_info for indices/forex
            volume = getattr(info, "three_month_average_volume", None) or 0

            results.append({
                "ticker":      symbol,
                "price":       round(float(price), 4),
                "open":        round(float(open_), 4) if open_ else None,
                "high":        round(float(high), 4)  if high  else None,
                "low":         round(float(low), 4)   if low   else None,
                "volume":      int(volume),
                "recorded_at": now,
            })
            log.info("  %-18s  %.4f", symbol, price)

        except Exception as e:
            log.warning("Could not fetch %s: %s", symbol, e)

    log.info("Fetched prices for %d / %d tickers", len(results), len(symbols))
    return results


def save_prices(prices: list[dict]) -> int:
    """
    Insert price rows. Skips if a record already exists for the same
    ticker within the last minute (avoids duplicate rows on re-runs).
    Returns the number of rows inserted.
    """
    if not prices:
        return 0

    inserted = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for p in prices:
                # Skip if we already have a record for this ticker within the last minute
                cur.execute(
                    """
                    SELECT 1 FROM prices
                    WHERE ticker = %s
                      AND recorded_at >= NOW() - INTERVAL '1 minute'
                    LIMIT 1
                    """,
                    (p["ticker"],),
                )
                if cur.fetchone():
                    continue

                cur.execute(
                    """
                    INSERT INTO prices (ticker, price, open, high, low, volume, recorded_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        p["ticker"],
                        p["price"],
                        p["open"],
                        p["high"],
                        p["low"],
                        p["volume"],
                        p["recorded_at"],
                    ),
                )
                inserted += 1
    log.info("Saved %d price records to DB", inserted)
    return inserted


def get_latest_prices(tickers: list[str] | None = None) -> dict[str, dict]:
    """
    Read the latest stored price for each ticker from the DB.
    Returns { symbol: {price, open, high, low, volume, recorded_at, change_pct} }
    """
    tickers = tickers or list(WATCHLIST_TICKERS.keys())

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (ticker)
                    ticker, price, open, high, low, volume, recorded_at
                FROM prices
                WHERE ticker = ANY(%s)
                ORDER BY ticker, recorded_at DESC
                """,
                (tickers,),
            )
            rows = cur.fetchall()

    result = {}
    for ticker, price, open_, high, low, volume, recorded_at in rows:
        change_pct = round(((price - open_) / open_) * 100, 2) if open_ else None
        result[ticker] = {
            "price":       price,
            "open":        open_,
            "high":        high,
            "low":         low,
            "volume":      volume,
            "recorded_at": recorded_at,
            "change_pct":  change_pct,
            "label":       WATCHLIST_TICKERS.get(ticker, ticker),
        }
    return result


def get_news_tickers() -> dict[str, str]:
    """
    Return tickers that have appeared in cluster_entities in the last 2 days.
    Combined with WATCHLIST_TICKERS (indices + macro), this covers the full
    Nifty 500 universe without fetching all 500 every refresh.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ce.ticker, ce.company_name
                FROM cluster_entities ce
                JOIN clusters c ON c.id = ce.cluster_id
                WHERE c.published_at >= NOW() - INTERVAL '2 days'
                """
            )
            rows = cur.fetchall()
    return {ticker: name for ticker, name in rows}


def run_all() -> None:
    # Always fetch watchlist (indices, macro, top stocks for the strip)
    tickers = dict(WATCHLIST_TICKERS)
    # Also fetch any tickers that appeared in recent news
    tickers.update(get_news_tickers())
    prices = fetch_prices(tickers)
    save_prices(prices)


if __name__ == "__main__":
    run_all()
