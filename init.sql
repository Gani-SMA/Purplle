-- Enable UUID generation extension if not natively loaded
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Table: stores
CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    layout JSONB NOT NULL, -- store_layout.json content
    open_hours JSONB NOT NULL,
    cameras JSONB NOT NULL, -- camera definitions
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Table: events
CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY, -- globally unique, from pipeline
    store_id VARCHAR(50) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(50) NOT NULL,
    visitor_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(30) NOT NULL, -- enum: ENTRY, EXIT, ZONE_ENTER, etc.
    timestamp TIMESTAMPTZ NOT NULL,
    zone_id VARCHAR(50), -- NULL for ENTRY/EXIT
    dwell_ms INTEGER NOT NULL DEFAULT 0,
    is_staff BOOLEAN NOT NULL DEFAULT false,
    confidence FLOAT NOT NULL,
    queue_depth INTEGER, -- from metadata
    sku_zone VARCHAR(100), -- from metadata
    session_seq INTEGER NOT NULL,
    raw_metadata JSONB, -- full metadata blob
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Table: sessions (materialized view -- computed on ingest)
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id VARCHAR(50) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    visitor_id VARCHAR(50) NOT NULL,
    entry_ts TIMESTAMPTZ NOT NULL,
    exit_ts TIMESTAMPTZ, -- NULL if still in store
    is_converted BOOLEAN NOT NULL DEFAULT false, -- POS correlated
    is_reentry BOOLEAN NOT NULL DEFAULT false,
    total_dwell_ms INTEGER,
    zones_visited TEXT[], -- array of zone_ids
    reached_billing BOOLEAN NOT NULL DEFAULT false,
    abandoned_queue BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Table: pos_transactions
CREATE TABLE IF NOT EXISTS pos_transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(50) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    basket_value NUMERIC(10,2) NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. Table: anomalies_log (audit trail)
CREATE TABLE IF NOT EXISTS anomalies_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id VARCHAR(50) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    anomaly_type VARCHAR(50) NOT NULL,
    severity VARCHAR(10) NOT NULL, -- INFO / WARN / CRITICAL
    message TEXT NOT NULL,
    suggested_action TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- --- Performance-Critical Indexes ---

-- Event queries are almost always filtered by store + time
CREATE INDEX IF NOT EXISTS idx_events_store_ts ON events(store_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_visitor ON events(visitor_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_staff ON events(is_staff) WHERE is_staff = false;

-- Session lookups by visitor (for re-entry dedup in funnel)
CREATE INDEX IF NOT EXISTS idx_sessions_visitor ON sessions(visitor_id, store_id);
CREATE INDEX IF NOT EXISTS idx_sessions_store_ts ON sessions(store_id, entry_ts DESC);

-- POS correlation: time-range lookup per store
CREATE INDEX IF NOT EXISTS idx_pos_store_ts ON pos_transactions(store_id, timestamp DESC);
