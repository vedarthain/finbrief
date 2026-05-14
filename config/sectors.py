"""
Sector mapping — ticker → sector
15 sectors + 3 macro buckets, organised under 5 super-groups.

Macro buckets ("Indices", "Commodities", "Forex") are excluded from the
Sector filter on the website; they appear in the macro/markets tabs.
"""

# Super-group order drives display order in the UI.
SUPER_GROUPS: dict[str, list[str]] = {
    "Financial Services": [
        "Banking",
        "NBFC & Capital Markets",
        "Insurance",
    ],
    "Technology": [
        "IT Services",
        "New-age Internet",
        "Telecom",
    ],
    "Consumer": [
        "Auto & Ancillaries",
        "FMCG",
        "Retail & Durables",
    ],
    "Industrials": [
        "Energy & Oil/Gas",
        "Power & Utilities",
        "Metals & Mining",
        "Capital Goods & Cement",
        "Infra & Realty",
    ],
    "Specialised": [
        "Pharma & Healthcare",
        "Defence & Aerospace",
        "Aviation & Logistics",
    ],
}

# Ordered flat list of all 15 sectors
SECTORS: list[str] = [s for group in SUPER_GROUPS.values() for s in group]

# Macro buckets — excluded from sector filter; shown separately
MACRO_BUCKETS = {"Indices", "Commodities", "Forex", "Global Indices"}


TICKER_SECTORS: dict[str, str] = {
    # ── Indices / Macro ──────────────────────────────────────────────────────
    "^NSEI": "Indices", "^BSESN": "Indices", "^NSEBANK": "Indices",
    "^NSEMDCP50": "Indices",
    "^CNXIT": "Indices", "^CNXPHARMA": "Indices", "^CNXAUTO": "Indices",
    "^CNXFMCG": "Indices", "^CNXMETAL": "Indices", "^CNXREALTY": "Indices",
    "^CNXINFRA": "Indices", "^CNXENERGY": "Indices", "^CNXPSUBANK": "Indices",
    "^GSPC": "Global Indices", "^IXIC": "Global Indices", "^DJI": "Global Indices",
    "^HSI":  "Global Indices", "^N225": "Global Indices", "^FTSE": "Global Indices",
    "^GDAXI": "Global Indices", "^STOXX50E": "Global Indices",
    "CL=F": "Commodities", "BZ=F": "Commodities",
    "GC=F": "Commodities", "SI=F": "Commodities",
    "USDINR=X": "Forex", "DX-Y.NYB": "Forex",

    # ── Banking ──────────────────────────────────────────────────────────────
    "HDFCBANK.NS": "Banking", "ICICIBANK.NS": "Banking", "SBIN.NS": "Banking",
    "AXISBANK.NS": "Banking", "KOTAKBANK.NS": "Banking", "INDUSINDBK.NS": "Banking",
    "YESBANK.NS": "Banking", "FEDERALBNK.NS": "Banking", "BANDHANBNK.NS": "Banking",
    "RBLBANK.NS": "Banking", "IDFCFIRSTB.NS": "Banking", "PNB.NS": "Banking",
    "CANBK.NS": "Banking", "BANKBARODA.NS": "Banking", "UNIONBANK.NS": "Banking",

    # ── NBFC & Capital Markets ───────────────────────────────────────────────
    "BAJFINANCE.NS": "NBFC & Capital Markets",
    "BAJAJFINSV.NS": "NBFC & Capital Markets",
    "CHOLAFIN.NS":   "NBFC & Capital Markets",
    "MUTHOOTFIN.NS": "NBFC & Capital Markets",
    "SHRIRAMFIN.NS": "NBFC & Capital Markets",
    "PFC.NS":        "NBFC & Capital Markets",
    "RECLTD.NS":     "NBFC & Capital Markets",
    "HDFCAMC.NS":    "NBFC & Capital Markets",
    "NAM-INDIA.NS":  "NBFC & Capital Markets",
    "MCX.NS":        "NBFC & Capital Markets",
    "BSE.NS":        "NBFC & Capital Markets",

    # ── Insurance ────────────────────────────────────────────────────────────
    "HDFCLIFE.NS": "Insurance", "SBILIFE.NS": "Insurance",
    "ICICIGI.NS": "Insurance", "ICICIPRULI.NS": "Insurance",
    "MFSL.NS": "Insurance", "LICI.NS": "Insurance",
    "STARHEALTH.NS": "Insurance",

    # ── IT Services ──────────────────────────────────────────────────────────
    "TCS.NS": "IT Services", "INFY.NS": "IT Services", "WIPRO.NS": "IT Services",
    "HCLTECH.NS": "IT Services", "TECHM.NS": "IT Services", "LTIM.NS": "IT Services",
    "MPHASIS.NS": "IT Services", "PERSISTENT.NS": "IT Services",
    "COFORGE.NS": "IT Services", "KPITTECH.NS": "IT Services",
    "TATAELXSI.NS": "IT Services", "OFSS.NS": "IT Services",
    "ZENSARTECH.NS": "IT Services", "HEXAWARE.NS": "IT Services",

    # ── New-age Internet ─────────────────────────────────────────────────────
    "PAYTM.NS": "New-age Internet", "ZOMATO.NS": "New-age Internet",
    "NYKAA.NS": "New-age Internet", "POLICYBZR.NS": "New-age Internet",
    "NAUKRI.NS": "New-age Internet", "INDIAMART.NS": "New-age Internet",
    "DIXON.NS": "New-age Internet", "KAYNES.NS": "New-age Internet",
    "SWIGGY.NS": "New-age Internet", "DELHIVERY.NS": "New-age Internet",

    # ── Telecom ──────────────────────────────────────────────────────────────
    "BHARTIARTL.NS": "Telecom", "IDEA.NS": "Telecom",
    "INDUSTOWER.NS": "Telecom", "TATACOMM.NS": "Telecom",

    # ── Auto & Ancillaries ───────────────────────────────────────────────────
    "MARUTI.NS": "Auto & Ancillaries",
    "TMCV.NS": "Auto & Ancillaries",            # Tata Motors parent (CV + JLR)
    "TMPV.NS": "Auto & Ancillaries",            # Tata Motors passenger vehicles
    "M&M.NS": "Auto & Ancillaries", "BAJAJ-AUTO.NS": "Auto & Ancillaries",
    "HEROMOTOCO.NS": "Auto & Ancillaries", "TVSMOTOR.NS": "Auto & Ancillaries",
    "EICHERMOT.NS": "Auto & Ancillaries", "ASHOKLEY.NS": "Auto & Ancillaries",
    "MOTHERSON.NS": "Auto & Ancillaries", "BOSCHLTD.NS": "Auto & Ancillaries",
    "MRF.NS": "Auto & Ancillaries", "APOLLOTYRE.NS": "Auto & Ancillaries",
    "CEATLTD.NS": "Auto & Ancillaries", "BHARATFORG.NS": "Auto & Ancillaries",
    "EXIDEIND.NS": "Auto & Ancillaries", "BALKRISIND.NS": "Auto & Ancillaries",

    # ── FMCG ─────────────────────────────────────────────────────────────────
    "HINDUNILVR.NS": "FMCG", "ITC.NS": "FMCG", "NESTLEIND.NS": "FMCG",
    "BRITANNIA.NS": "FMCG", "DABUR.NS": "FMCG", "MARICO.NS": "FMCG",
    "GODREJCP.NS": "FMCG", "COLPAL.NS": "FMCG", "EMAMILTD.NS": "FMCG",
    "VBL.NS": "FMCG", "TATACONSUM.NS": "FMCG", "UNITDSPR.NS": "FMCG",
    "RADICO.NS": "FMCG", "UBL.NS": "FMCG", "PATANJALI.NS": "FMCG",

    # ── Retail & Durables ────────────────────────────────────────────────────
    "TITAN.NS": "Retail & Durables", "DMART.NS": "Retail & Durables",
    "TRENT.NS": "Retail & Durables", "KALYANKJIL.NS": "Retail & Durables",
    "VMART.NS": "Retail & Durables", "SHOPERSTOP.NS": "Retail & Durables",
    "PAGEIND.NS": "Retail & Durables",
    "HAVELLS.NS": "Retail & Durables", "VOLTAS.NS": "Retail & Durables",
    "CROMPTON.NS": "Retail & Durables", "BLUESTARCO.NS": "Retail & Durables",
    "WHIRLPOOL.NS": "Retail & Durables", "TTKPRESTIG.NS": "Retail & Durables",
    "PIDILITIND.NS": "Retail & Durables", "ASIANPAINT.NS": "Retail & Durables",
    "BERGEPAINT.NS": "Retail & Durables", "KANSAINER.NS": "Retail & Durables",

    # ── Energy & Oil/Gas ─────────────────────────────────────────────────────
    "RELIANCE.NS": "Energy & Oil/Gas", "ONGC.NS": "Energy & Oil/Gas",
    "BPCL.NS": "Energy & Oil/Gas", "IOC.NS": "Energy & Oil/Gas",
    "HINDPETRO.NS": "Energy & Oil/Gas", "PETRONET.NS": "Energy & Oil/Gas",
    "GAIL.NS": "Energy & Oil/Gas", "ATGL.NS": "Energy & Oil/Gas",
    "IGL.NS": "Energy & Oil/Gas", "MGL.NS": "Energy & Oil/Gas",

    # ── Power & Utilities ────────────────────────────────────────────────────
    "NTPC.NS": "Power & Utilities", "POWERGRID.NS": "Power & Utilities",
    "TATAPOWER.NS": "Power & Utilities", "JSWENERGY.NS": "Power & Utilities",
    "TORNTPOWER.NS": "Power & Utilities", "CESC.NS": "Power & Utilities",
    "NHPC.NS": "Power & Utilities", "SJVN.NS": "Power & Utilities",
    "IREDA.NS": "Power & Utilities", "ADANIGREEN.NS": "Power & Utilities",
    "ADANIPOWER.NS": "Power & Utilities", "SUZLON.NS": "Power & Utilities",

    # ── Metals & Mining ──────────────────────────────────────────────────────
    "TATASTEEL.NS": "Metals & Mining", "JSWSTEEL.NS": "Metals & Mining",
    "HINDALCO.NS": "Metals & Mining", "VEDL.NS": "Metals & Mining",
    "SAIL.NS": "Metals & Mining", "NMDC.NS": "Metals & Mining",
    "NATIONALUM.NS": "Metals & Mining", "HINDZINC.NS": "Metals & Mining",
    "COALINDIA.NS": "Metals & Mining", "JINDALSTEL.NS": "Metals & Mining",
    "APLAPOLLO.NS": "Metals & Mining",

    # ── Capital Goods & Cement ───────────────────────────────────────────────
    "LT.NS": "Capital Goods & Cement",
    "ABB.NS": "Capital Goods & Cement", "SIEMENS.NS": "Capital Goods & Cement",
    "BHEL.NS": "Capital Goods & Cement", "CUMMINSIND.NS": "Capital Goods & Cement",
    "THERMAX.NS": "Capital Goods & Cement", "KEC.NS": "Capital Goods & Cement",
    "KPIL.NS": "Capital Goods & Cement",
    "ULTRACEMCO.NS": "Capital Goods & Cement", "AMBUJACEM.NS": "Capital Goods & Cement",
    "ACC.NS": "Capital Goods & Cement", "SHREECEM.NS": "Capital Goods & Cement",
    "JKCEMENT.NS": "Capital Goods & Cement", "DALBHARAT.NS": "Capital Goods & Cement",
    "RAMCOCEM.NS": "Capital Goods & Cement",

    # ── Infra & Realty ───────────────────────────────────────────────────────
    "ADANIENT.NS": "Infra & Realty",
    "ADANIPORTS.NS": "Infra & Realty", "GMRINFRA.NS": "Infra & Realty",
    "IRCON.NS": "Infra & Realty", "RITES.NS": "Infra & Realty",
    "IRFC.NS": "Infra & Realty", "RVNL.NS": "Infra & Realty",
    "DLF.NS": "Infra & Realty", "GODREJPROP.NS": "Infra & Realty",
    "PRESTIGE.NS": "Infra & Realty", "OBEROIRLTY.NS": "Infra & Realty",
    "PHOENIXLTD.NS": "Infra & Realty", "BRIGADE.NS": "Infra & Realty",
    "SOBHA.NS": "Infra & Realty", "MACROTECH.NS": "Infra & Realty",

    # ── Pharma & Healthcare ──────────────────────────────────────────────────
    "SUNPHARMA.NS": "Pharma & Healthcare", "DRREDDY.NS": "Pharma & Healthcare",
    "CIPLA.NS": "Pharma & Healthcare", "DIVISLAB.NS": "Pharma & Healthcare",
    "LUPIN.NS": "Pharma & Healthcare", "AUROPHARMA.NS": "Pharma & Healthcare",
    "BIOCON.NS": "Pharma & Healthcare", "ABBOTINDIA.NS": "Pharma & Healthcare",
    "ALKEM.NS": "Pharma & Healthcare", "IPCALAB.NS": "Pharma & Healthcare",
    "TORNTPHARM.NS": "Pharma & Healthcare", "ZYDUSLIFE.NS": "Pharma & Healthcare",
    "GLAND.NS": "Pharma & Healthcare",
    "APOLLOHOSP.NS": "Pharma & Healthcare", "MAXHEALTH.NS": "Pharma & Healthcare",
    "FORTIS.NS": "Pharma & Healthcare", "NH.NS": "Pharma & Healthcare",
    "PIIND.NS": "Pharma & Healthcare", "SRF.NS": "Pharma & Healthcare",

    # ── Defence & Aerospace ──────────────────────────────────────────────────
    "HAL.NS": "Defence & Aerospace", "BEL.NS": "Defence & Aerospace",
    "MAZDOCK.NS": "Defence & Aerospace", "COCHINSHIP.NS": "Defence & Aerospace",
    "GRSE.NS": "Defence & Aerospace", "BDL.NS": "Defence & Aerospace",
    "DATAPATTNS.NS": "Defence & Aerospace",

    # ── Aviation & Logistics ─────────────────────────────────────────────────
    "INDIGO.NS": "Aviation & Logistics",
    "SPICEJET.BO": "Aviation & Logistics",
    "CONCOR.NS": "Aviation & Logistics", "GATI.NS": "Aviation & Logistics",
    "BLUEDART.NS": "Aviation & Logistics", "TCI.NS": "Aviation & Logistics",
    "MAHLOG.NS": "Aviation & Logistics",
}


def sector_for(ticker: str) -> str:
    """Return the sector for a ticker, or 'Other' if unknown."""
    return TICKER_SECTORS.get(ticker, "Other")


def super_group_for(sector: str) -> str | None:
    """Return the super-group for a sector, or None if it's a macro bucket / Other."""
    for group, members in SUPER_GROUPS.items():
        if sector in members:
            return group
    return None
