-- SkyCache catalog schema (SQLite)
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS packages (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    priority_class TEXT NOT NULL,
    title_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    languages_json TEXT NOT NULL,
    received_at TEXT NOT NULL,
    freshness_hours INTEGER NOT NULL DEFAULT 72,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    license TEXT NOT NULL DEFAULT 'unknown',
    source_json TEXT NOT NULL,
    files_json TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    pinned INTEGER NOT NULL DEFAULT 0,
    icon TEXT,
    path TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_packages_class ON packages(priority_class);
CREATE INDEX IF NOT EXISTS idx_packages_score ON packages(score DESC);
CREATE INDEX IF NOT EXISTS idx_packages_received ON packages(received_at DESC);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    level TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    meta_json TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Nexus 0.4 community services (local-only; no third-party analytics)
CREATE TABLE IF NOT EXISTS package_ratings (
    package_id TEXT NOT NULL,
    voter_token TEXT NOT NULL,
    stars INTEGER NOT NULL CHECK (stars >= 1 AND stars <= 5),
    created_at TEXT NOT NULL,
    PRIMARY KEY (package_id, voter_token)
);

CREATE TABLE IF NOT EXISTS board_posts (
    id TEXT PRIMARY KEY,
    board TEXT NOT NULL DEFAULT 'general',
    author TEXT NOT NULL DEFAULT 'anonymous',
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    pinned INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_board_posts_board ON board_posts(board, created_at DESC);

CREATE TABLE IF NOT EXISTS content_requests (
    id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    priority_class TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
);
