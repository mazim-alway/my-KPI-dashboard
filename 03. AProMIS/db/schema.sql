-- ============================================================
--  APro-MIS KPI DATABASE SCHEMA
--  Derived from Excel structure in "APro-MIS ver3 (LQH5 Series)"
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- USERS TABLE (Login identity, optional future RBAC)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    display_name    TEXT,
    role            TEXT DEFAULT 'user',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Default admin (optional)
INSERT OR IGNORE INTO users (username, display_name, role)
VALUES ('admin', 'System Administrator', 'admin');



-- ============================================================
-- THEMES TABLE (Theme 1, Theme 2, ADHOC, etc.)
-- ============================================================
CREATE TABLE IF NOT EXISTS themes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_name      TEXT NOT NULL UNIQUE
);



-- ============================================================
-- PERIOD TABLE (24F2, 25F1, etc.)
-- ============================================================
CREATE TABLE IF NOT EXISTS periods (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    period_code     TEXT NOT NULL UNIQUE,
    description     TEXT
);



-- ============================================================
-- PROJECT MASTER TABLE
--    This merges ALL your sheet structures:
--    24F2, 25F1, ADHOC, Training, IPC, Technical Reports, etc.
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign Keys
    theme_id            INTEGER,
    period_id           INTEGER,

    -- Core Project Fields (from XLSM)
    project_name        TEXT NOT NULL,
    product_item        TEXT,
    process_name        TEXT,
    details             TEXT,           -- Additional detail column (from sheet4)
    deadline            DATE,
    remark              TEXT,

    registered_by       TEXT,
    registered_on       DATETIME,
    status              TEXT,           -- COMPLETE / IN-PROGRESS / OVERDUE
    kpi_value           REAL,           -- KPI summary values

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(theme_id) REFERENCES themes(id),
    FOREIGN KEY(period_id) REFERENCES periods(id)
);



-- ============================================================
-- STATUS HISTORY TABLE
-- Tracks changes over time (optional but very useful)
-- ============================================================
CREATE TABLE IF NOT EXISTS status_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL,
    old_status      TEXT,
    new_status      TEXT,
    changed_by      TEXT,
    changed_on      DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(project_id) REFERENCES projects(id)
);



-- ============================================================
-- KPI SUMMARY TABLE
-- Stores period results (e.g. Total completed, Overall KPI)
-- Based on repeating fields in your Excel sheets.
-- ============================================================
CREATE TABLE IF NOT EXISTS kpi_summary (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id           INTEGER NOT NULL,
    theme_id            INTEGER,
    total_registered    INTEGER,
    total_completed     INTEGER,
    total_overdue       INTEGER,
    overall_kpi         REAL,

    generated_on        DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(period_id) REFERENCES periods(id),
    FOREIGN KEY(theme_id) REFERENCES themes(id)
);



-- ============================================================
-- INDEXES FOR PERFORMANCE (Recommended for multi-user SQLite)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_projects_period
    ON projects(period_id);

CREATE INDEX IF NOT EXISTS idx_projects_theme
    ON projects(theme_id);

CREATE INDEX IF NOT EXISTS idx_projects_status
    ON projects(status);

CREATE INDEX IF NOT EXISTS idx_kpi_summary_period
    ON kpi_summary(period_id);

