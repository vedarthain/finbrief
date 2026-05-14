-- FinBrief Database Schema
-- Idempotent — safe to run multiple times (all CREATE IF NOT EXISTS)

-- ── Raw ingested headlines ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_items (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    body            TEXT,
    published_at    TIMESTAMPTZ,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_processed    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_raw_items_fetched_at   ON raw_items (fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_items_is_processed ON raw_items (is_processed);
CREATE INDEX IF NOT EXISTS idx_raw_items_source       ON raw_items (source);


-- ── Price snapshots ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prices (
    id          SERIAL PRIMARY KEY,
    ticker      TEXT NOT NULL,
    price       NUMERIC(14, 4),
    open        NUMERIC(14, 4),
    high        NUMERIC(14, 4),
    low         NUMERIC(14, 4),
    volume      BIGINT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker_time ON prices (ticker, recorded_at DESC);


-- ── Clustered + synthesised stories ────────────────────────────────────────
-- One cluster = one real-world event, deduped across sources
CREATE TABLE IF NOT EXISTS clusters (
    id               SERIAL PRIMARY KEY,
    headline         TEXT NOT NULL,         -- LLM-written crisp headline
    summary          TEXT NOT NULL,         -- 50-word synthesis (house style)
    importance_score INTEGER DEFAULT 0,     -- 0-100, drives "top 5" selection
    category         TEXT,                  -- markets | economy | companies | macro
    country          TEXT DEFAULT 'IN',
    published_at     TIMESTAMPTZ,           -- earliest raw_item in this cluster
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_top_story     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_clusters_published   ON clusters (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_top_story   ON clusters (is_top_story, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_importance  ON clusters (importance_score DESC);


-- ── Which raw items make up each cluster ────────────────────────────────────
CREATE TABLE IF NOT EXISTS cluster_items (
    cluster_id  INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    raw_item_id INTEGER NOT NULL REFERENCES raw_items(id) ON DELETE CASCADE,
    PRIMARY KEY (cluster_id, raw_item_id)
);


-- ── Tickers mentioned in each cluster + price at publish time ───────────────
-- This is the news→price impact table
CREATE TABLE IF NOT EXISTS cluster_entities (
    id              SERIAL PRIMARY KEY,
    cluster_id      INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    ticker          TEXT NOT NULL,          -- e.g. 'HDFCBANK.NS'
    company_name    TEXT,                   -- e.g. 'HDFC Bank'

    -- Price snapshot AT the time the cluster was published
    price_at_publish    NUMERIC(14, 4),
    recorded_at_publish TIMESTAMPTZ,

    -- Price snapshot MOST RECENTLY fetched (updated by price_fetcher runs)
    price_latest        NUMERIC(14, 4),
    recorded_at_latest  TIMESTAMPTZ,

    -- Derived: % move since the story broke
    -- Recomputed each time price_fetcher runs: ((latest - at_publish) / at_publish) * 100
    price_change_pct    NUMERIC(8, 4),

    -- Direction tag for easy UI rendering
    direction   TEXT GENERATED ALWAYS AS (
        CASE
            WHEN price_change_pct > 0.5  THEN 'up'
            WHEN price_change_pct < -0.5 THEN 'down'
            ELSE 'flat'
        END
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_cluster_entities_cluster  ON cluster_entities (cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_entities_ticker   ON cluster_entities (ticker);


-- ── Daily morning brief snapshot ────────────────────────────────────────────
-- One row per day — the "5 things before the bell" rendered that morning
CREATE TABLE IF NOT EXISTS daily_brief (
    id          SERIAL PRIMARY KEY,
    brief_date  DATE NOT NULL UNIQUE,
    cluster_ids INTEGER[] NOT NULL,         -- ordered list of top-story cluster IDs
    markets_snapshot JSONB,                 -- { "^NSEI": {price, chg_pct}, ... }
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_brief_date ON daily_brief (brief_date DESC);
