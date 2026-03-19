from db.connection import get_connection
from datetime import datetime

# =========================================================
# AUTO INITIALIZE THEMES IF EMPTY (so joins return names)
# =========================================================
def ensure_default_themes():
    """
    Ensure the 'themes' table contains the five default themes.
    Runs once on module import.
    """
    default_themes = [
        "920A01: Build a safe, secure, and healthy workplace.",
        "920A02: Realize automotive quality manufacturing",
        "920A03: Rebuild profit-making power for the next expansion",
        "920A04: Give employees a sense of growth & be respected by community",
        "ADHOC / Customer Claim / CAPA"
    ]
    conn = get_connection()
    cur = conn.cursor()

    # If the table is empty, seed it
    cur.execute("SELECT COUNT(*) FROM themes")
    if cur.fetchone()[0] == 0:
        for t in default_themes:
            cur.execute("INSERT INTO themes (theme_name) VALUES (?)", (t,))
        conn.commit()

    conn.close()

# Ensure themes exist at import time
ensure_default_themes()


# =========================================================
# THEMES CRUD
# =========================================================
def get_all_themes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, theme_name FROM themes ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return rows


# =========================================================
# PERIODS CRUD
# =========================================================
def get_all_periods():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, period_code, description
        FROM periods
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


# =========================================================
# PROJECTS CRUD
# =========================================================
def add_project(theme_id, period_id, project_name, product_item, process_name,
                details, deadline, remark, registered_by, registered_on,
                status, kpi_value):
    """
    Insert a project row. theme_id and period_id are FKs.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO projects (
            theme_id, period_id, project_name, product_item, process_name,
            details, deadline, remark, registered_by, registered_on,
            status, kpi_value, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (
        theme_id, period_id, project_name, product_item, process_name,
        details, deadline, remark, registered_by, registered_on,
        status, kpi_value
    ))

    conn.commit()
    conn.close()


def update_project(project_id, theme_id, period_id, project_name,
                   product_item, process_name, details, deadline,
                   remark, status, kpi_value):
    """
    Update a project row by id. theme_id and period_id are FKs.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE projects SET
            theme_id     = ?,
            period_id    = ?,
            project_name = ?,
            product_item = ?,
            process_name = ?,
            details      = ?,
            deadline     = ?,
            remark       = ?,
            status       = ?,
            kpi_value    = ?,
            updated_at   = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        theme_id, period_id, project_name, product_item, process_name,
        details, deadline, remark, status, kpi_value, project_id
    ))

    conn.commit()
    conn.close()

def update_project_status(project_id: int, new_status: str):
    """
    Update only the status (and updated_at) for a project.
    Safe, minimal update used by submission flow.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE projects
           SET status = ?,
               updated_at = CURRENT_TIMESTAMP
         WHERE id = ?
    """, (new_status, project_id))
    conn.commit()
    conn.close()


def log_status_change_safe(project_id: int, old_status: str, new_status: str, changed_by: str = None):
    """
    Try to write a row into status_history, but don't fail if the table doesn't exist.
    Use this as a best-effort audit trail.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO status_history (project_id, old_status, new_status, changed_by, changed_on)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (project_id, old_status, new_status, changed_by))
        conn.commit()
        conn.close()
    except Exception:
        # Silently ignore if status_history doesn't exist
        pass


def delete_project(project_id):
    conn = get_connection()
    cur = conn.cursor()
    # Delete related status history first (if exists)
    cur.execute("DELETE FROM status_history WHERE project_id = ?", (project_id,))
    cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


def get_all_projects():
    """
    Returns all projects with joined theme + period info.
    Column order (used by UI):
      0 id,
      1 theme_name,
      2 period_code,
      3 project_name,
      4 product_item,
      5 process_name,
      6 details,
      7 deadline,
      8 remark,
      9 registered_by,
      10 registered_on,
      11 status,
      12 kpi_value,
      13 created_at,
      14 updated_at
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.id,
            t.theme_name,
            pr.period_code,
            p.project_name,
            p.product_item,
            p.process_name,
            p.details,
            p.deadline,
            p.remark,
            p.registered_by,
            p.registered_on,
            p.status,
            p.kpi_value,
            p.created_at,
            p.updated_at
        FROM projects p
        LEFT JOIN themes  t  ON p.theme_id  = t.id
        LEFT JOIN periods pr ON p.period_id = pr.id
        ORDER BY p.id DESC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def search_projects(keyword: str):
    """
    Search projects across multiple fields (joins theme & period).
    Returns the SAME column order as get_all_projects().
    """
    conn = get_connection()
    cur = conn.cursor()
    like = f"%{keyword}%"

    cur.execute("""
        SELECT
            p.id,
            t.theme_name,
            pr.period_code,
            p.project_name,
            p.product_item,
            p.process_name,
            p.details,
            p.deadline,
            p.remark,
            p.registered_by,
            p.registered_on,
            p.status,
            p.kpi_value,
            p.created_at,
            p.updated_at
        FROM projects p
        LEFT JOIN themes  t  ON p.theme_id  = t.id
        LEFT JOIN periods pr ON p.period_id = pr.id
        WHERE
               p.project_name        LIKE ?
            OR p.product_item        LIKE ?
            OR p.process_name        LIKE ?
            OR p.remark              LIKE ?
            OR IFNULL(t.theme_name,'')  LIKE ?
            OR IFNULL(pr.period_code,'') LIKE ?
        ORDER BY p.id DESC
    """, (like, like, like, like, like, like))

    rows = cur.fetchall()
    conn.close()
    return rows


# =========================================================
# KPI SUMMARY (used by analytics_page)
# =========================================================
def calculate_period_kpi(period_id: int):
    """
    Calculates KPI summary for Analytics page:
      - total_registered
      - total_completed
      - total_overdue
      - overall_kpi (completed / registered * 100)
    """
    conn = get_connection()
    cur = conn.cursor()

    # Total registered
    cur.execute("SELECT COUNT(*) FROM projects WHERE period_id = ?", (period_id,))
    total_registered = cur.fetchone()[0]

    # Completed
    cur.execute("""
        SELECT COUNT(*)
        FROM projects
        WHERE period_id = ? AND status = 'COMPLETE'
    """, (period_id,))
    total_completed = cur.fetchone()[0]

    # Overdue
    cur.execute("""
        SELECT COUNT(*)
        FROM projects
        WHERE period_id = ? AND status = 'OVERDUE'
    """, (period_id,))
    total_overdue = cur.fetchone()[0]

    # KPI (%)
    overall_kpi = round((total_completed / total_registered) * 100, 2) if total_registered > 0 else 0.0

    conn.close()
    return {
        "total_registered": total_registered,
        "total_completed":  total_completed,
        "total_overdue":    total_overdue,
        "overall_kpi":      overall_kpi
    }

# =======================
# PUBLICATIONS (Research)
# =======================
def _table_has_column(conn, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols

def ensure_publications_table():
    """
    Create a simple publications table if it doesn't exist.
    Add pdf_path column if migrating from older version.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            authors TEXT NOT NULL,
            venue TEXT NOT NULL,
            year INTEGER NOT NULL,
            abstract TEXT,
            tags TEXT,
            figure_paths TEXT, -- semicolon-separated list of image file paths
            pdf_path TEXT,     -- optional path to a single PDF
            link TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration: add pdf_path if missing
    if not _table_has_column(conn, "publications", "pdf_path"):
        try:
            cur.execute("ALTER TABLE publications ADD COLUMN pdf_path TEXT")
            conn.commit()
        except Exception:
            pass
    conn.close()

def add_publication(title, authors, venue, year, abstract, tags, figure_paths, pdf_path, link):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO publications
            (title, authors, venue, year, abstract, tags, figure_paths, pdf_path, link, created_at, updated_at)
        VALUES
            (?,     ?,       ?,     ?,    ?,        ?,    ?,            ?,        ?,   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (title, authors, venue, int(year), abstract, tags, figure_paths, pdf_path, link))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid

def get_publications():
    """
    Return a list of dicts:
      id, title, authors, venue, year, abstract, tags, figure_paths, pdf_path, link, created_at, updated_at
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, authors, venue, year, abstract, tags, figure_paths, pdf_path, link, created_at, updated_at
        FROM publications
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    keys = ["id","title","authors","venue","year","abstract","tags","figure_paths","pdf_path","link","created_at","updated_at"]
    return [dict(zip(keys, r)) for r in rows]

def delete_publication(pub_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM publications WHERE id = ?", (pub_id,))
    conn.commit()
    conn.close()