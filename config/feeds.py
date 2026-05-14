"""
Central config for all RSS sources and watchlist tickers.
Add / remove feeds here — the ingester picks them up automatically.

Sources marked ❌ have killed/blocked their public RSS as of 2025.
"""

RSS_FEEDS = [
    # ── India — Markets & Economy ───────────────────────────────────────────
    {
        "source": "moneycontrol",
        "url": "https://www.moneycontrol.com/rss/latestnews.xml",
        "country": "IN",
        "category": "markets",
    },
    {
        "source": "livemint_markets",
        "url": "https://www.livemint.com/rss/markets",
        "country": "IN",
        "category": "markets",
    },
    {
        "source": "livemint_companies",
        "url": "https://www.livemint.com/rss/companies",
        "country": "IN",
        "category": "companies",
    },
    {
        "source": "economic_times_markets",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "country": "IN",
        "category": "markets",
    },
    {
        "source": "economic_times_economy",
        "url": "https://economictimes.indiatimes.com/news/economy/rssfeeds/20169977.cms",
        "country": "IN",
        "category": "economy",
    },
    {
        "source": "economic_times_companies",
        "url": "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms",
        "country": "IN",
        "category": "companies",
    },
    {
        "source": "hindu_businessline",
        "url": "https://www.thehindubusinessline.com/markets/?service=rss",
        "country": "IN",
        "category": "markets",
    },
    {
        "source": "ndtv_profit",
        "url": "https://feeds.feedburner.com/ndtvprofit-latest",
        "country": "IN",
        "category": "markets",
    },
    {
        "source": "zeebiz",
        "url": "https://www.zeebiz.com/rss.xml",
        "country": "IN",
        "category": "markets",
    },
    # ET sector-specific feeds
    {
        "source": "et_banking",
        "url": "https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358575.cms",
        "country": "IN",
        "category": "companies",
    },
    {
        "source": "et_tech",
        "url": "https://economictimes.indiatimes.com/industry/tech/rssfeeds/13357270.cms",
        "country": "IN",
        "category": "companies",
    },
    {
        "source": "et_auto",
        "url": "https://economictimes.indiatimes.com/industry/auto/rssfeeds/13357323.cms",
        "country": "IN",
        "category": "companies",
    },
    {
        "source": "et_pharma",
        "url": "https://economictimes.indiatimes.com/industry/healthcare/biotech/pharmaceuticals/rssfeeds/13358078.cms",
        "country": "IN",
        "category": "companies",
    },
    {
        "source": "et_energy",
        "url": "https://economictimes.indiatimes.com/industry/energy/rssfeeds/13358935.cms",
        "country": "IN",
        "category": "companies",
    },
    {
        "source": "et_policy",
        "url": "https://economictimes.indiatimes.com/news/economy/policy/rssfeeds/20169957.cms",
        "country": "IN",
        "category": "economy",
    },
    {
        "source": "et_indicators",
        "url": "https://economictimes.indiatimes.com/news/economy/indicators/rssfeeds/20169963.cms",
        "country": "IN",
        "category": "economy",
    },
    {
        "source": "livemint_economy",
        "url": "https://www.livemint.com/rss/economy",
        "country": "IN",
        "category": "economy",
    },
    {
        "source": "livemint_politics",
        "url": "https://www.livemint.com/rss/politics",
        "country": "IN",
        "category": "economy",
    },
    {
        "source": "hindu_bl_companies",
        "url": "https://www.thehindubusinessline.com/companies/?service=rss",
        "country": "IN",
        "category": "companies",
    },
    {
        "source": "hindu_bl_economy",
        "url": "https://www.thehindubusinessline.com/economy/?service=rss",
        "country": "IN",
        "category": "economy",
    },
    {
        "source": "moneycontrol_markets",
        "url": "https://www.moneycontrol.com/rss/marketreports.xml",
        "country": "IN",
        "category": "markets",
    },
    {
        "source": "moneycontrol_business",
        "url": "https://www.moneycontrol.com/rss/business.xml",
        "country": "IN",
        "category": "companies",
    },

    # ── NOT available via public RSS (blocked/discontinued) ─────────────────
    # ❌ Business Standard   — RSS disabled, returns broken XML
    # ❌ Financial Express   — RSS removed
    # ❌ CNBCTV18            — RSS blocked
    # ❌ BQ Prime            — No public RSS
    # ❌ Business Today      — No public RSS

    # ── Global overnight context ────────────────────────────────────────────
    {
        "source": "cnbc_world",
        "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "country": "GLOBAL",
        "category": "markets",
    },
    {
        "source": "cnbc_finance",
        "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "country": "GLOBAL",
        "category": "economy",
    },
    {
        "source": "marketwatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "country": "GLOBAL",
        "category": "markets",
    },
    {
        "source": "ft_markets",
        "url": "https://www.ft.com/markets?format=rss",
        "country": "GLOBAL",
        "category": "markets",
    },
    {
        "source": "ft_economy",
        "url": "https://www.ft.com/global-economy?format=rss",
        "country": "GLOBAL",
        "category": "economy",
    },
    {
        "source": "cnbc_asia",
        "url": "https://www.cnbc.com/id/19832390/device/rss/rss.html",
        "country": "GLOBAL",
        "category": "markets",
    },
    {
        "source": "cnbc_investing",
        "url": "https://www.cnbc.com/id/15839069/device/rss/rss.html",
        "country": "GLOBAL",
        "category": "markets",
    },
    {
        "source": "investing_com_commodities",
        "url": "https://www.investing.com/rss/news_14.rss",
        "country": "GLOBAL",
        "category": "macro",
    },
    {
        "source": "investing_com_forex",
        "url": "https://www.investing.com/rss/news_1.rss",
        "country": "GLOBAL",
        "category": "macro",
    },
]


# ── BSE / NSE corporate announcements ───────────────────────────────────────
# Polled separately via ingestion/exchange_fetcher.py (not RSS)
BSE_ANNOUNCEMENT_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/AnnGetAnnouncementsDetails/w"
    "?strCat=-1&strType=C&strScrip=&strSearch=P&strToDate=&strFromDate=&myClient="
)
NSE_ANNOUNCEMENT_URL = (
    "https://www.nseindia.com/api/corporate-announcements?index=equities"
)


# ── Watchlist tickers ────────────────────────────────────────────────────────
# Yahoo Finance symbols: .NS = NSE, ^ = index, =X = forex, =F = futures
WATCHLIST_TICKERS = {
    # Indian Indices
    "^NSEI":     "Nifty 50",
    "^BSESN":    "Sensex",
    "^NSEBANK":  "Bank Nifty",
    "^NSEMDCP50": "Nifty Midcap 50",

    # Large Cap — Diversified
    "RELIANCE.NS":   "Reliance Inds",
    "TCS.NS":        "TCS",
    "HDFCBANK.NS":   "HDFC Bank",
    "INFY.NS":       "Infosys",
    "ICICIBANK.NS":  "ICICI Bank",
    "WIPRO.NS":      "Wipro",
    "ADANIENT.NS":   "Adani Ent",
    "MARUTI.NS":     "Maruti Suzuki",
    "LT.NS":         "L&T",
    "SBIN.NS":       "SBI",
    "BAJFINANCE.NS": "Bajaj Finance",
    "AXISBANK.NS":   "Axis Bank",
    "KOTAKBANK.NS":  "Kotak Bank",
    "HINDUNILVR.NS": "HUL",
    "ITC.NS":        "ITC",
    "SUNPHARMA.NS":  "Sun Pharma",
    "ONGC.NS":       "ONGC",
    "NTPC.NS":       "NTPC",
    "POWERGRID.NS":  "Power Grid",

    # Global Macro
    "^GSPC":    "S&P 500",
    "^IXIC":    "Nasdaq",
    "^HSI":     "Hang Seng",
    "^N225":    "Nikkei 225",
    "GC=F":     "Gold",
    "CL=F":     "Crude Oil (WTI)",
    "BZ=F":     "Crude Oil (Brent)",
    "USDINR=X": "USD/INR",
    "DX-Y.NYB": "Dollar Index",
}
