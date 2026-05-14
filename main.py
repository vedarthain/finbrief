"""
FinBrief — main entry point
----------------------------
Full pipeline:
  1. Init DB schema
  2. Fetch RSS feeds → raw_items
  3. Fetch prices → prices
  4. LLM clustering + synthesis → clusters / cluster_entities
  5. Refresh price impact on all entities

Usage:
    python main.py               # full pipeline
    python main.py --init-only   # only create tables
    python main.py --no-llm      # skip LLM step (just ingest + prices)
    python main.py --prices-only # only refresh prices + impact
"""

import argparse
import logging

from db.connection import init_schema
from ingestion.rss_fetcher import run_all as fetch_rss
from ingestion.price_fetcher import run_all as fetch_prices
from ingestion.llm_pipeline import run_all as run_llm, update_price_impact
from ingestion.daily_history import (
    run_all as fetch_daily_history,
    update_performance_pcts,
    backfill_sectors,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="FinBrief ingestion pipeline")
    parser.add_argument("--init-only",   action="store_true")
    parser.add_argument("--no-llm",      action="store_true")
    parser.add_argument("--prices-only", action="store_true")
    args = parser.parse_args()

    log.info("── Initialising schema ─────────────────────────")
    init_schema()

    if args.init_only:
        log.info("Schema ready. Exiting."); return

    if args.prices_only:
        log.info("── Refreshing prices ───────────────────────────")
        fetch_prices()
        log.info("── Updating price impact ───────────────────────")
        update_price_impact()
        log.info("── Done ────────────────────────────────────────"); return

    log.info("── Fetching RSS feeds ──────────────────────────")
    fetch_rss()

    log.info("── Fetching prices ─────────────────────────────")
    fetch_prices()

    if not args.no_llm:
        log.info("── Running LLM pipeline ────────────────────────")
        run_llm()

    log.info("── Backfilling sectors + 1W/1M performance ─────")
    backfill_sectors()
    update_performance_pcts()

    log.info("── Pipeline complete ───────────────────────────")


if __name__ == "__main__":
    main()
