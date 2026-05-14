"""
LLM Pipeline — Cluster, Synthesise, Tag, Score
------------------------------------------------
Uses Google Gemini Flash (free tier — no credit card needed).
Free limits: 15 req/min, 1M tokens/day — more than enough.

Picks up unprocessed raw_items, calls Gemini to:
  1. Cluster stories about the same event (dedupe across sources)
  2. Write a crisp 50-word synthesis per cluster (house style)
  3. Extract company/index names mentioned
  4. Score importance 0-100
  5. Persist to clusters / cluster_items / cluster_entities
  6. Snapshot price_at_publish for each tagged ticker

Get your free key → https://aistudio.google.com (no credit card)

Run standalone:
    python -m ingestion.llm_pipeline
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher

from google import genai
from google.genai import types
from dotenv import load_dotenv

from config.feeds import WATCHLIST_TICKERS
from db.connection import get_conn

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)

MODEL         = "gemini-2.5-flash-lite"
MODEL_FALLBACK = "gemini-3.1-flash-lite"   # fallback if primary hits daily quota

# ── Ticker lookup: company name → Yahoo Finance symbol ──────────────────────
TICKER_ALIASES: dict[str, str] = {
    v.lower(): k for k, v in WATCHLIST_TICKERS.items()
}
TICKER_ALIASES.update({
    # ── Indices ──────────────────────────────────────────────────────────────
    "nifty":               "^NSEI",
    "nifty 50":            "^NSEI",
    "nifty50":             "^NSEI",
    "sensex":              "^BSESN",
    "bse sensex":          "^BSESN",
    "bank nifty":          "^NSEBANK",
    "banknifty":           "^NSEBANK",
    "nifty bank":          "^NSEBANK",
    "nifty midcap":        "^NSEMDCP50",
    "nifty it":            "^CNXIT",
    "nifty pharma":        "^CNXPHARMA",
    "nifty auto":          "^CNXAUTO",
    "nifty fmcg":          "^CNXFMCG",
    "nifty metal":         "^CNXMETAL",
    "nifty realty":        "^CNXREALTY",
    "nifty infra":         "^CNXINFRA",
    "nifty energy":        "^CNXENERGY",
    "nifty psu bank":      "^CNXPSUBANK",

    # ── Global macro ─────────────────────────────────────────────────────────
    "s&p 500":             "^GSPC",
    "s&p":                 "^GSPC",
    "nasdaq":              "^IXIC",
    "dow":                 "^DJI",
    "dow jones":           "^DJI",
    "fed":                 "^GSPC",
    "federal reserve":     "^GSPC",
    "crude":               "CL=F",
    "crude oil":           "CL=F",
    "wti":                 "CL=F",
    "brent":               "BZ=F",
    "brent crude":         "BZ=F",
    "gold":                "GC=F",
    "silver":              "SI=F",
    "rupee":               "USDINR=X",
    "inr":                 "USDINR=X",
    "usd/inr":             "USDINR=X",
    "dollar index":        "DX-Y.NYB",

    # ── Nifty 500 — Large Cap ────────────────────────────────────────────────
    "reliance":                "RELIANCE.NS",
    "reliance industries":     "RELIANCE.NS",
    "ril":                     "RELIANCE.NS",
    "tcs":                     "TCS.NS",
    "tata consultancy":        "TCS.NS",
    "tata consultancy services": "TCS.NS",
    "hdfc bank":               "HDFCBANK.NS",
    "hdfcbank":                "HDFCBANK.NS",
    "infosys":                 "INFY.NS",
    "infy":                    "INFY.NS",
    "icici bank":              "ICICIBANK.NS",
    "icici":                   "ICICIBANK.NS",
    "wipro":                   "WIPRO.NS",
    "adani enterprises":       "ADANIENT.NS",
    "adani ent":               "ADANIENT.NS",
    "adani":                   "ADANIENT.NS",
    "maruti":                  "MARUTI.NS",
    "maruti suzuki":           "MARUTI.NS",
    "l&t":                     "LT.NS",
    "larsen":                  "LT.NS",
    "larsen & toubro":         "LT.NS",
    "larsen and toubro":       "LT.NS",
    "sbi":                     "SBIN.NS",
    "state bank":              "SBIN.NS",
    "state bank of india":     "SBIN.NS",
    "bajaj finance":           "BAJFINANCE.NS",
    "bajfinance":              "BAJFINANCE.NS",
    "axis bank":               "AXISBANK.NS",
    "axis":                    "AXISBANK.NS",
    "kotak":                   "KOTAKBANK.NS",
    "kotak bank":              "KOTAKBANK.NS",
    "kotak mahindra":          "KOTAKBANK.NS",
    "kotak mahindra bank":     "KOTAKBANK.NS",
    "hul":                     "HINDUNILVR.NS",
    "hindustan unilever":      "HINDUNILVR.NS",
    "itc":                     "ITC.NS",
    "sun pharma":              "SUNPHARMA.NS",
    "sun pharmaceutical":      "SUNPHARMA.NS",
    "ongc":                    "ONGC.NS",
    "ntpc":                    "NTPC.NS",
    "power grid":              "POWERGRID.NS",
    "powergrid":               "POWERGRID.NS",
    # Auto
    "tata motors":             "TATAMOTORS.NS",
    "tatamotors":              "TATAMOTORS.NS",
    "hero motocorp":           "HEROMOTOCO.NS",
    "hero moto":               "HEROMOTOCO.NS",
    "hero":                    "HEROMOTOCO.NS",
    "bajaj auto":              "BAJAJ-AUTO.NS",
    "tvs motor":               "TVSMOTOR.NS",
    "tvs":                     "TVSMOTOR.NS",
    "eicher motors":           "EICHERMOT.NS",
    "royal enfield":           "EICHERMOT.NS",
    "eicher":                  "EICHERMOT.NS",
    "mahindra":                "M&M.NS",
    "m&m":                     "M&M.NS",
    "mahindra & mahindra":     "M&M.NS",
    "ashok leyland":           "ASHOKLEY.NS",
    "motherson":               "MOTHERSON.NS",
    "samvardhana motherson":   "MOTHERSON.NS",
    "bosch":                   "BOSCHLTD.NS",
    "mrf":                     "MRF.NS",
    "apollo tyres":            "APOLLOTYRE.NS",
    "apollo tyre":             "APOLLOTYRE.NS",
    "ceat":                    "CEATLTD.NS",
    # Banks & Financials
    "yes bank":                "YESBANK.NS",
    "indusind bank":           "INDUSINDBK.NS",
    "indusind":                "INDUSINDBK.NS",
    "federal bank":            "FEDERALBNK.NS",
    "bandhan bank":            "BANDHANBNK.NS",
    "rbl bank":                "RBLBANK.NS",
    "idfc first bank":         "IDFCFIRSTB.NS",
    "idfc first":              "IDFCFIRSTB.NS",
    "idfc":                    "IDFCFIRSTB.NS",
    "pnb":                     "PNB.NS",
    "punjab national bank":    "PNB.NS",
    "canara bank":             "CANBK.NS",
    "bank of baroda":          "BANKBARODA.NS",
    "bob":                     "BANKBARODA.NS",
    "union bank":              "UNIONBANK.NS",
    "bajaj finserv":           "BAJAJFINSV.NS",
    "hdfc life":               "HDFCLIFE.NS",
    "sbi life":                "SBILIFE.NS",
    "icici lombard":           "ICICIGI.NS",
    "icici prudential":        "ICICIPRULI.NS",
    "max financial":           "MFSL.NS",
    "hdfc amc":                "HDFCAMC.NS",
    "nippon amc":              "NAM-INDIA.NS",
    "nippon india":            "NAM-INDIA.NS",
    "lic":                     "LICI.NS",
    "life insurance corporation": "LICI.NS",
    "muthoot finance":         "MUTHOOTFIN.NS",
    "muthoot":                 "MUTHOOTFIN.NS",
    "shriram finance":         "SHRIRAMFIN.NS",
    "shriram":                 "SHRIRAMFIN.NS",
    "cholamandalam":           "CHOLAFIN.NS",
    "chola":                   "CHOLAFIN.NS",
    "pfc":                     "PFC.NS",
    "power finance":           "PFC.NS",
    "rec":                     "RECLTD.NS",
    "rural electrification":   "RECLTD.NS",
    # IT & Tech
    "hcl tech":                "HCLTECH.NS",
    "hcl technologies":        "HCLTECH.NS",
    "hcl":                     "HCLTECH.NS",
    "tech mahindra":           "TECHM.NS",
    "techm":                   "TECHM.NS",
    "ltimindtree":             "LTIM.NS",
    "lti mindtree":            "LTIM.NS",
    "mindtree":                "LTIM.NS",
    "mphasis":                 "MPHASIS.NS",
    "persistent systems":      "PERSISTENT.NS",
    "persistent":              "PERSISTENT.NS",
    "coforge":                 "COFORGE.NS",
    "kpit technologies":       "KPITTECH.NS",
    "kpit":                    "KPITTECH.NS",
    "tata elxsi":              "TATAELXSI.NS",
    "oracle financial":        "OFSS.NS",
    "ofss":                    "OFSS.NS",
    "zensar":                  "ZENSARTECH.NS",
    "hexaware":                "HEXAWARE.NS",
    "paytm":                   "PAYTM.NS",
    "one97":                   "PAYTM.NS",
    "zomato":                  "ZOMATO.NS",
    "swiggy":                  "SWIGGY.NS",
    "nykaa":                   "NYKAA.NS",
    "fss":                     "FSS.NS",
    "policy bazaar":           "POLICYBZR.NS",
    "policybazaar":            "POLICYBZR.NS",
    "info edge":               "NAUKRI.NS",
    "naukri":                  "NAUKRI.NS",
    "indiamart":               "INDIAMART.NS",
    "dixon technologies":      "DIXON.NS",
    "dixon":                   "DIXON.NS",
    "kaynes technology":       "KAYNES.NS",
    # Pharma & Healthcare
    "dr reddy":                "DRREDDY.NS",
    "dr reddy's":              "DRREDDY.NS",
    "cipla":                   "CIPLA.NS",
    "divi's":                  "DIVISLAB.NS",
    "divis labs":              "DIVISLAB.NS",
    "divis":                   "DIVISLAB.NS",
    "lupin":                   "LUPIN.NS",
    "aurobindo":               "AUROPHARMA.NS",
    "aurobindo pharma":        "AUROPHARMA.NS",
    "biocon":                  "BIOCON.NS",
    "abbott india":            "ABBOTINDIA.NS",
    "alkem":                   "ALKEM.NS",
    "ipca":                    "IPCALAB.NS",
    "torrent pharma":          "TORNTPHARM.NS",
    "torrent pharmaceuticals": "TORNTPHARM.NS",
    "zydus":                   "ZYDUSLIFE.NS",
    "zydus lifesciences":      "ZYDUSLIFE.NS",
    "gland pharma":            "GLAND.NS",
    "max healthcare":          "MAXHEALTH.NS",
    "apollo hospitals":        "APOLLOHOSP.NS",
    "apollo":                  "APOLLOHOSP.NS",
    "fortis":                  "FORTIS.NS",
    "narayana hrudayalaya":    "NH.NS",
    # FMCG & Consumer
    "nestle":                  "NESTLEIND.NS",
    "nestle india":            "NESTLEIND.NS",
    "britannia":               "BRITANNIA.NS",
    "dabur":                   "DABUR.NS",
    "marico":                  "MARICO.NS",
    "godrej consumer":         "GODREJCP.NS",
    "gcpl":                    "GODREJCP.NS",
    "colgate":                 "COLPAL.NS",
    "colgate palmolive":       "COLPAL.NS",
    "emami":                   "EMAMILTD.NS",
    "vbl":                     "VBL.NS",
    "varun beverages":         "VBL.NS",
    "tata consumer":           "TATACONSUM.NS",
    "tata consumer products":  "TATACONSUM.NS",
    "united spirits":          "MCDOWELL-N.NS",
    "diageo india":            "MCDOWELL-N.NS",
    "radico khaitan":          "RADICO.NS",
    "united breweries":        "UBL.NS",
    "titan":                   "TITAN.NS",
    "titan company":           "TITAN.NS",
    "kalyan jewellers":        "KALYANKJIL.NS",
    "kalyani":                 "KALYANKJIL.NS",
    # Retail & Consumer Discretionary
    "dmart":                   "DMART.NS",
    "avenue supermarts":       "DMART.NS",
    "trent":                   "TRENT.NS",
    "zara india":              "TRENT.NS",
    "v-mart":                  "VMART.NS",
    "shoppers stop":           "SHOPERSTOP.NS",
    "page industries":         "PAGEIND.NS",
    "jockey":                  "PAGEIND.NS",
    # Cement & Building Materials
    "ultratech":               "ULTRACEMCO.NS",
    "ultratech cement":        "ULTRACEMCO.NS",
    "ambuja cement":           "AMBUJACEM.NS",
    "ambuja":                  "AMBUJACEM.NS",
    "acc":                     "ACC.NS",
    "shree cement":            "SHREECEM.NS",
    "shree":                   "SHREECEM.NS",
    "jk cement":               "JKCEMENT.NS",
    "dalmia bharat":           "DALBHARAT.NS",
    "ramco cement":            "RAMCOCEM.NS",
    "pidilite":                "PIDILITIND.NS",
    "asian paints":            "ASIANPAINT.NS",
    "berger paints":           "BERGEPAINT.NS",
    "kansai nerolac":          "KANSAINER.NS",
    # Metals & Mining
    "tata steel":              "TATASTEEL.NS",
    "jsw steel":               "JSWSTEEL.NS",
    "jsw":                     "JSWSTEEL.NS",
    "hindalco":                "HINDALCO.NS",
    "vedanta":                 "VEDL.NS",
    "steel authority":         "SAIL.NS",
    "sail":                    "SAIL.NS",
    "nmdc":                    "NMDC.NS",
    "nalco":                   "NATIONALUM.NS",
    "national aluminium":      "NATIONALUM.NS",
    "hindustan zinc":          "HINDZINC.NS",
    "hinduzinc":               "HINDZINC.NS",
    "coalindia":               "COALINDIA.NS",
    "coal india":              "COALINDIA.NS",
    # Energy & Oil
    "bpcl":                    "BPCL.NS",
    "bharat petroleum":        "BPCL.NS",
    "ioc":                     "IOC.NS",
    "indian oil":              "IOC.NS",
    "hpcl":                    "HINDPETRO.NS",
    "hindustan petroleum":     "HINDPETRO.NS",
    "petronet lng":            "PETRONET.NS",
    "petronet":                "PETRONET.NS",
    "gail":                    "GAIL.NS",
    "adani green":             "ADANIGREEN.NS",
    "adani power":             "ADANIPOWER.NS",
    "adani ports":             "ADANIPORTS.NS",
    "adani total gas":         "ATGL.NS",
    "adani wilmar":            "AWL.NS",
    "tata power":              "TATAPOWER.NS",
    "jsw energy":              "JSWENERGY.NS",
    "torrent power":           "TORNTPOWER.NS",
    "cesc":                    "CESC.NS",
    "nhpc":                    "NHPC.NS",
    "sjvn":                    "SJVN.NS",
    "ireda":                   "IREDA.NS",
    # Telecom & Media
    "airtel":                  "BHARTIARTL.NS",
    "bharti airtel":           "BHARTIARTL.NS",
    "jio":                     "RELIANCE.NS",
    "vodafone idea":           "IDEA.NS",
    "vi":                      "IDEA.NS",
    "idea":                    "IDEA.NS",
    "indus towers":            "INDUSTOWER.NS",
    "zee entertainment":       "ZEEL.NS",
    "zee":                     "ZEEL.NS",
    "sun tv":                  "SUNTV.NS",
    "dish tv":                 "DISHTV.NS",
    # Infrastructure & Real Estate
    "dlf":                     "DLF.NS",
    "godrej properties":       "GODREJPROP.NS",
    "prestige":                "PRESTIGE.NS",
    "oberoi realty":           "OBEROIRLTY.NS",
    "phoenix mills":           "PHOENIXLTD.NS",
    "brigade":                 "BRIGADE.NS",
    "sobha":                   "SOBHA.NS",
    "ircon":                   "IRCON.NS",
    "rites":                   "RITES.NS",
    "irfc":                    "IRFC.NS",
    "rvnl":                    "RVNL.NS",
    "rail vikas":              "RVNL.NS",
    "gmr airports":            "GMRINFRA.NS",
    "gmr":                     "GMRINFRA.NS",
    "abb india":               "ABB.NS",
    "abb":                     "ABB.NS",
    "siemens":                 "SIEMENS.NS",
    "bhel":                    "BHEL.NS",
    "bharat heavy electricals": "BHEL.NS",
    # Diversified / Conglomerates
    "tata group":              "TATAMOTORS.NS",
    "itc group":               "ITC.NS",
    "aditya birla":            "HINDALCO.NS",
    "godrej":                  "GODREJCP.NS",
    "havells":                 "HAVELLS.NS",
    "voltas":                  "VOLTAS.NS",
    "crompton":                "CROMPTON.NS",
    "blue star":               "BLUESTARCO.NS",
    "whirlpool":               "WHIRLPOOL.NS",
    "ttk prestige":            "TTKPRESTIG.NS",
    # Aviation & Logistics
    "interglobe":              "INDIGO.NS",
    "indigo":                  "INDIGO.NS",
    "spicejet":                "SPICEJET.NS",
    "air india":               "AIRINDIA.NS",
    "container corporation":   "CONCOR.NS",
    "concor":                  "CONCOR.NS",
    "gati":                    "GATI.NS",
    "delhivery":               "DELHIVERY.NS",
    "blue dart":               "BLUEDART.NS",
    # Chemicals & Specialty
    "pi industries":           "PIIND.NS",
    "pi ind":                  "PIIND.NS",
    "srf":                     "SRF.NS",
    "aarti industries":        "AARTIIND.NS",
    "aarti":                   "AARTIIND.NS",
    "deepak nitrite":          "DEEPAKNTR.NS",
    "tata chemicals":          "TATACHEM.NS",
    "navin fluorine":          "NAVINFLUOR.NS",
    "clean science":           "CLEAN.NS",
    "galaxe":                  "GALAXYSURF.NS",
    "galaxy surfactants":      "GALAXYSURF.NS",
    # Defence & Capital Goods
    "hal":                     "HAL.NS",
    "hindustan aeronautics":   "HAL.NS",
    "bel":                     "BEL.NS",
    "bharat electronics":      "BEL.NS",
    "mazagon dock":            "MAZDOCK.NS",
    "cochin shipyard":         "COCHINSHIP.NS",
    "garden reach":            "GRSE.NS",
    "bharat forge":            "BHARATFORG.NS",
    "cummins":                 "CUMMINSIND.NS",
    "thermax":                 "THERMAX.NS",
    "kec international":       "KEC.NS",
    "kalpataru":               "KPIL.NS",
    # RBI / Regulators (map to indices)
    "rbi":                     "^NSEI",
    "reserve bank":            "^NSEI",
    "reserve bank of india":   "^NSEI",
    "sebi":                    "^NSEI",
    "government of india":     "^NSEI",
    "finance ministry":        "^NSEI",
    "budget":                  "^NSEI",
})


# ── Editorial system prompt ──────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the editorial engine for FinBrief, an Indian financial news platform for analytical investors.

HOUSE STYLE — follow exactly:
1. Lead with the NUMBER or entity. "Reliance Q4 net profit ₹18,951 cr, up 12% YoY — refining margins offset a 4% retail revenue dip." NOT "Reliance reported strong results."
2. Sentence 2: why it matters + one concrete data point or comparison.
3. Sentence 3: sector read-across or what analysts/investors should watch.
4. Hard limit: 100 words, 12-word headline.
5. No naked adjectives. Every claim needs a number. Ban: stunning, massive, significant, key, major, strong, robust, notable, impressive.
6. End with (Source: <shortest pub name>).
7. No investment advice. Uncertainty = "may", "could". No predictions as facts.
8. Units: ₹ cr for crore, ₹ bn for billion, % not "percent". For forex: $ mn / $ bn.
9. For earnings: always state PAT + revenue + margin + YoY delta if available.

IMPORTANCE SCORE GUIDE — be strict, most stories score 40-65:
- 88-100: Market-halting events only. RBI rate change, Union Budget, index constituent earnings beat/miss >10%, govt ban/approval on major sector.
- 72-87: Notable but not systemic. Nifty 50 stock quarterly results, SEBI order, large M&A (>₹1,000 cr), sector policy shift.
- 55-71: Informative. Mid-cap results, industry data releases, analyst upgrades/downgrades.
- 35-54: Routine. Smaller company news, global spillover without direct India impact, regulatory filings.
- Below 35: Brief mentions, minor updates, speculative reports.

COUNTRY RULES:
- country = "IN" → India-specific: companies, RBI, SEBI, BSE/NSE, Indian economy, Indian sectors
- country = "GLOBAL" → International macro WITH direct India impact: Fed, crude, dollar, China only

CLUSTERING RULE:
- Same event reported by multiple sources = ONE cluster (pick best details from each)
- Different events = separate clusters

OUTPUT: Return ONLY a valid JSON array. No markdown, no explanation, just the raw JSON array."""


# ── JSON schema for Gemini response ─────────────────────────────────────────
RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "headline": {
                "type": "string",
                "description": "Crisp 12-word headline. Lead with number or entity name.",
            },
            "summary": {
                "type": "string",
                "description": "Max 100 words. House style: number first, context + why-it-matters, what to watch, attribution.",
            },
            "category": {
                "type": "string",
                "enum": ["markets", "economy", "companies", "macro"],
            },
            "country": {
                "type": "string",
                "enum": ["IN", "GLOBAL"],
            },
            "importance_score": {
                "type": "integer",
                "description": "0-100. 80+ = top story. Earnings, RBI/SEBI actions, sector events score high.",
            },
            "tickers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Company/index names mentioned e.g. 'HDFC Bank', 'Nifty', 'Reliance'. Plain names only.",
            },
            "raw_item_indices": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "0-based indices of input headlines that belong to this cluster.",
            },
        },
        "required": [
            "headline", "summary", "category", "country",
            "importance_score", "tickers", "raw_item_indices",
        ],
    },
}


def _resolve_ticker(name: str) -> str | None:
    return TICKER_ALIASES.get(name.lower().strip())


def _get_latest_price_from_db(ticker: str) -> tuple[float | None, datetime | None]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT price, recorded_at FROM prices
                WHERE ticker = %s
                ORDER BY recorded_at DESC LIMIT 1
                """,
                (ticker,),
            )
            row = cur.fetchone()
    if row:
        return float(row[0]), row[1]
    return None, None


def fetch_unprocessed(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source, title, body, published_at
                FROM raw_items
                WHERE is_processed = FALSE
                ORDER BY fetched_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    return [
        {"id": r[0], "source": r[1], "title": r[2],
         "body": r[3], "published_at": r[4]}
        for r in rows
    ]


def call_gemini(items: list[dict]) -> list[dict]:
    """
    Send a batch of raw items to Gemini Flash.
    Returns list of cluster dicts.
    Free tier: 15 req/min — we batch everything into 1-2 calls.
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    payload = [
        {"i": idx, "title": it["title"], "source": it["source"]}
        for idx, it in enumerate(items)
    ]

    prompt = (
        "Cluster these headlines into distinct events. "
        "Dedupe — same story from multiple sources = one cluster. "
        "Return JSON array only.\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    log.info("Sending %d items to Gemini Flash …", len(items))

    # Retry up to 4 times on 503/overload with exponential backoff.
    # On 429 QUOTA_EXHAUSTED (daily limit hit), fail immediately — no point retrying.
    last_err = None
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    temperature=0.1,
                    max_output_tokens=16000,
                ),
            )
            last_err = None
            break
        except Exception as e:
            last_err = e
            err_str = str(e)
            # Daily quota exhausted → try fallback model immediately
            if "GenerateRequestsPerDayPerProjectPerModel" in err_str or "quota" in err_str.lower():
                log.warning("Daily quota exhausted for %s — switching to fallback %s", MODEL, MODEL_FALLBACK)
                try:
                    response = client.models.generate_content(
                        model=MODEL_FALLBACK,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            response_schema=RESPONSE_SCHEMA,
                            temperature=0.1,
                            max_output_tokens=16000,
                        ),
                    )
                    last_err = None
                except Exception as e2:
                    last_err = e2
                break
            wait = 15 * (2 ** attempt)   # 15s, 30s, 60s, 120s
            log.warning("Attempt %d failed (%s). Retrying in %ds …", attempt + 1, type(e).__name__, wait)
            time.sleep(wait)

    if last_err:
        log.error("All retries exhausted: %s", last_err)
        return []

    raw = response.text or ""
    log.debug("Raw response preview: %s", raw[:300])

    # Strip markdown code fences if the model wrapped output in ```json ... ```
    if raw.strip().startswith("```"):
        raw = raw.strip().lstrip("`").lstrip("json").rstrip("`").strip()

    try:
        clusters = json.loads(raw)
        log.info("Gemini returned %d clusters", len(clusters))
        return clusters
    except (json.JSONDecodeError, TypeError) as e:
        log.error("JSON parse failed: %s", e)
        log.error("Response tail (last 300 chars): …%s", raw[-300:])
        return []


def save_clusters(clusters: list[dict], raw_items: list[dict]) -> int:
    if not clusters:
        return 0

    saved = 0
    now = datetime.now(tz=timezone.utc)
    processed_ids: list[int] = []

    with get_conn() as conn:
        with conn.cursor() as cur:
            for cl in clusters:
                indices = cl.get("raw_item_indices", [])

                # published_at = earliest raw item in this cluster
                pub_dates = [
                    raw_items[i]["published_at"]
                    for i in indices
                    if i < len(raw_items) and raw_items[i]["published_at"]
                ]
                published_at = min(pub_dates) if pub_dates else now

                is_top = int(cl.get("importance_score", 0)) >= 75

                cur.execute(
                    """
                    INSERT INTO clusters
                        (headline, summary, importance_score, category,
                         country, published_at, is_top_story)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        cl["headline"],
                        cl["summary"],
                        cl.get("importance_score", 50),
                        cl.get("category", "markets"),
                        cl.get("country", "IN"),
                        published_at,
                        is_top,
                    ),
                )
                cluster_id = cur.fetchone()[0]

                # Link raw items → cluster
                for idx in indices:
                    if idx < len(raw_items):
                        cur.execute(
                            """
                            INSERT INTO cluster_items (cluster_id, raw_item_id)
                            VALUES (%s, %s) ON CONFLICT DO NOTHING
                            """,
                            (cluster_id, raw_items[idx]["id"]),
                        )
                        processed_ids.append(raw_items[idx]["id"])

                # Resolve tickers → snapshot price_at_publish
                seen_tickers: set[str] = set()
                for name in cl.get("tickers", []):
                    ticker = _resolve_ticker(name)
                    if not ticker or ticker in seen_tickers:
                        continue
                    seen_tickers.add(ticker)
                    price, rec_at = _get_latest_price_from_db(ticker)
                    cur.execute(
                        """
                        INSERT INTO cluster_entities
                            (cluster_id, ticker, company_name,
                             price_at_publish, recorded_at_publish,
                             price_latest, recorded_at_latest, price_change_pct)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            cluster_id, ticker, name,
                            price, rec_at,
                            price, rec_at,
                            0.0,
                        ),
                    )

                saved += 1

            # Mark all contributing raw items as processed
            if processed_ids:
                cur.execute(
                    "UPDATE raw_items SET is_processed = TRUE WHERE id = ANY(%s)",
                    (list(set(processed_ids)),),
                )

    log.info("Saved %d clusters, marked %d raw items processed",
             saved, len(set(processed_ids)))
    return saved


def dedup_clusters(threshold: float = 0.82) -> int:
    """
    Remove near-duplicate clusters created when the same story slipped into
    multiple batches.  For every pair of clusters on the same IST date +
    country whose headlines are ≥ threshold similar, keep the one with the
    higher importance_score (ties → keep the earlier id) and delete the other.
    Returns the number of clusters removed.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Pull all clusters from the last 2 days (covers any overnight run)
            cur.execute(
                """
                SELECT id, headline, importance_score, country,
                       (published_at AT TIME ZONE 'Asia/Kolkata')::date AS ist_date
                FROM clusters
                WHERE published_at >= NOW() - INTERVAL '2 days'
                ORDER BY ist_date, country, id
                """
            )
            rows = cur.fetchall()

    # Group by (ist_date, country)
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for row in rows:
        cid, headline, score, country, ist_date = row
        groups[(str(ist_date), country)].append(
            {"id": cid, "headline": headline or "", "score": int(score or 0)}
        )

    def _word_jaccard(a: str, b: str) -> float:
        """Word-level Jaccard similarity — catches 'Sept' vs 'September' variants."""
        # Strip common stop words so content words drive the score
        stop = {"a","an","the","in","on","at","to","of","for","and","or","as",
                "is","are","was","were","its","it","by","from","with","that",
                "this","has","have","had","be","been","will","may","could"}
        wa = {w for w in a.lower().split() if w not in stop and len(w) > 2}
        wb = {w for w in b.lower().split() if w not in stop and len(w) > 2}
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    to_delete: set[int] = set()
    for items in groups.values():
        n = len(items)
        for i in range(n):
            if items[i]["id"] in to_delete:
                continue
            for j in range(i + 1, n):
                if items[j]["id"] in to_delete:
                    continue
                h1 = items[i]["headline"].lower()
                h2 = items[j]["headline"].lower()
                char_ratio = SequenceMatcher(None, h1, h2).ratio()
                word_ratio = _word_jaccard(h1, h2)
                # Duplicate if EITHER metric is high enough
                if char_ratio >= threshold or word_ratio >= 0.60:
                    loser = items[j] if items[i]["score"] >= items[j]["score"] else items[i]
                    to_delete.add(loser["id"])

    if not to_delete:
        log.info("Dedup: no near-duplicate clusters found.")
        return 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Cascade: delete cluster_items + cluster_entities first
            cur.execute(
                "DELETE FROM cluster_items   WHERE cluster_id = ANY(%s)",
                (list(to_delete),),
            )
            cur.execute(
                "DELETE FROM cluster_entities WHERE cluster_id = ANY(%s)",
                (list(to_delete),),
            )
            cur.execute(
                "DELETE FROM clusters WHERE id = ANY(%s)",
                (list(to_delete),),
            )
    log.info("Dedup: removed %d duplicate cluster(s).", len(to_delete))
    return len(to_delete)


def update_price_impact() -> None:
    """Refresh price_latest + price_change_pct on all cluster_entities."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE cluster_entities ce
                SET
                    price_latest       = p.price,
                    recorded_at_latest = p.recorded_at,
                    price_change_pct   = CASE
                        WHEN ce.price_at_publish IS NOT NULL
                         AND ce.price_at_publish <> 0
                        THEN ROUND(
                            ((p.price - ce.price_at_publish)
                             / ce.price_at_publish * 100)::numeric, 4)
                        ELSE 0
                    END
                FROM (
                    SELECT DISTINCT ON (ticker)
                        ticker, price, recorded_at
                    FROM prices
                    ORDER BY ticker, recorded_at DESC
                ) p
                WHERE ce.ticker = p.ticker
                """
            )
            log.info("Updated price impact for %d entities", cur.rowcount)


def run_all(batch_size: int = 50) -> None:
    """
    Full pipeline: fetch ALL unprocessed → call Gemini in batches → save → update prices.
    No cap — processes everything in the queue each run.
    Batch size of 50 keeps each Gemini call comfortably within token limits.
    """
    items = fetch_unprocessed(limit=10000)   # fetch everything unprocessed
    if not items:
        log.info("No unprocessed items. Nothing to do.")
        return

    log.info("Processing %d unprocessed raw items …", len(items))
    total_batches = (len(items) - 1) // batch_size + 1
    total_saved = 0

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        log.info("Batch %d/%d (%d items) …", i // batch_size + 1, total_batches, len(batch))
        clusters = call_gemini(batch)
        total_saved += save_clusters(clusters, batch)

        # Respect free tier rate limit — pause between batches
        if i + batch_size < len(items):
            log.info("Pausing 6s for rate limit …")
            time.sleep(6)

    dedup_clusters()
    update_price_impact()
    log.info("Pipeline done. Total clusters saved: %d", total_saved)


if __name__ == "__main__":
    run_all()
