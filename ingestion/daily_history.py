"""
Daily Price History — backfill + maintain `prices_daily` table.

Uses yfinance.history(period="1mo") to fetch the last ~30 daily closes for each
ticker. Inserts into `prices_daily` (idempotent — ON CONFLICT DO NOTHING).

Then computes price_change_1w_pct + price_change_1m_pct on cluster_entities.

Run via:
    python -m ingestion.daily_history          # backfill all entities + watchlist
"""

import logging
from datetime import datetime, timezone

import yfinance as yf

from config.feeds import WATCHLIST_TICKERS
from config.sectors import sector_for
from db.connection import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)


def fetch_daily_history(ticker: str, period: str = "1mo") -> list[dict]:
    """Fetch daily OHLCV for the past `period`. Returns list of dicts ready to insert."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d", auto_adjust=False)
        if df.empty:
            return []
        rows = []
        for ts, row in df.iterrows():
            rows.append({
                "ticker": ticker,
                "date":   ts.date(),
                "close":  float(row["Close"])  if row["Close"]  == row["Close"] else None,
                "open":   float(row["Open"])   if row["Open"]   == row["Open"]  else None,
                "high":   float(row["High"])   if row["High"]   == row["High"]  else None,
                "low":    float(row["Low"])    if row["Low"]    == row["Low"]   else None,
                "volume": int(row["Volume"])   if row["Volume"] == row["Volume"] else 0,
            })
        return rows
    except Exception as e:
        log.warning("Failed history for %s: %s", ticker, e)
        return []


def save_daily(rows: list[dict]) -> int:
    if not rows:
        return 0
    n = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO prices_daily (ticker, date, close, open, high, low, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, date) DO UPDATE
                      SET close=EXCLUDED.close, open=EXCLUDED.open,
                          high=EXCLUDED.high, low=EXCLUDED.low, volume=EXCLUDED.volume
                    """,
                    (r["ticker"], r["date"], r["close"], r["open"],
                     r["high"], r["low"], r["volume"]),
                )
                n += 1
    return n


def tickers_to_backfill() -> set[str]:
    """All tickers that appear in cluster_entities or WATCHLIST_TICKERS."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT ticker FROM cluster_entities")
            from_entities = {r[0] for r in cur.fetchall()}
    return from_entities | set(WATCHLIST_TICKERS.keys())


def update_performance_pcts() -> None:
    """
    Compute price_change_1w_pct and price_change_1m_pct on cluster_entities
    from prices_daily snapshots (newest close vs 5-trading-day / 22-trading-day ago).
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (ticker) ticker, close, date
                    FROM prices_daily
                    ORDER BY ticker, date DESC
                ),
                week_ago AS (
                    SELECT DISTINCT ON (pd.ticker) pd.ticker, pd.close
                    FROM prices_daily pd
                    WHERE pd.date <= CURRENT_DATE - INTERVAL '5 days'
                    ORDER BY pd.ticker, pd.date DESC
                ),
                month_ago AS (
                    SELECT DISTINCT ON (pd.ticker) pd.ticker, pd.close
                    FROM prices_daily pd
                    WHERE pd.date <= CURRENT_DATE - INTERVAL '22 days'
                    ORDER BY pd.ticker, pd.date DESC
                )
                UPDATE cluster_entities ce
                SET
                    price_change_1w_pct = CASE
                        WHEN w.close IS NOT NULL AND w.close <> 0
                        THEN ROUND(((l.close - w.close) / w.close * 100)::numeric, 4)
                        ELSE NULL END,
                    price_change_1m_pct = CASE
                        WHEN m.close IS NOT NULL AND m.close <> 0
                        THEN ROUND(((l.close - m.close) / m.close * 100)::numeric, 4)
                        ELSE NULL END
                FROM latest l
                LEFT JOIN week_ago  w ON w.ticker = l.ticker
                LEFT JOIN month_ago m ON m.ticker = l.ticker
                WHERE ce.ticker = l.ticker
                """
            )
            log.info("Updated 1W/1M performance on %d entities", cur.rowcount)


def backfill_sectors() -> None:
    """Populate the sector column on all cluster_entities."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT ticker FROM cluster_entities WHERE sector IS NULL")
            tickers = [r[0] for r in cur.fetchall()]
            for t in tickers:
                cur.execute(
                    "UPDATE cluster_entities SET sector = %s WHERE ticker = %s",
                    (sector_for(t), t),
                )
            log.info("Backfilled sector for %d distinct tickers", len(tickers))


def run_all() -> None:
    tickers = sorted(tickers_to_backfill())
    log.info("Backfilling daily history for %d tickers …", len(tickers))
    total = 0
    for i, t in enumerate(tickers, 1):
        rows = fetch_daily_history(t)
        n = save_daily(rows)
        total += n
        if i % 20 == 0:
            log.info("  … %d/%d (saved %d rows so far)", i, len(tickers), total)
    log.info("Saved %d daily price rows total", total)

    backfill_sectors()
    update_performance_pcts()


if __name__ == "__main__":
    run_all()
