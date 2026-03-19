import streamlit as st
import pandas as pd
import datetime
import calendar

from db.queries import (
    get_all_projects,
    get_all_periods,   # optional; we’ll fall back to periods in data if empty
    get_all_themes     # DB master to keep theme sequence/FK in sync
)

# -----------------------------------------------------------
# Utility: safe date parsing
# -----------------------------------------------------------
def _to_date(x):
    """
    Best-effort convert to date. Returns None if invalid.
    Accepts 'YYYY-MM-DD', datetime/date objects, or None.
    """
    if not x:
        return None
    try:
        if isinstance(x, (datetime.date, datetime.datetime)):
            return x.date() if isinstance(x, datetime.datetime) else x
        return pd.to_datetime(x).date()
    except Exception:
        return None


# -----------------------------------------------------------
# Utility: get start/end range for a project row
# Start = registered_on (idx 10) if present else created_at (idx 13)
# End   = deadline (idx 7) or start if missing
# Schema (from get_all_projects JOIN):
#   0 id, 1 theme_name, 2 period_code, 3 project_name, 4 product_item,
#   5 process_name, 6 details, 7 deadline, 8 remark, 9 registered_by,
#   10 registered_on, 11 status, 12 kpi_value, 13 created_at, 14 updated_at
# -----------------------------------------------------------
def _project_date_range(row):
    registered_on = _to_date(row[10])  # registered_on
    created_at    = _to_date(row[13])  # created_at
    deadline      = _to_date(row[7])   # deadline
    start = registered_on or created_at
    end   = deadline or start
    return (start, end)


# -----------------------------------------------------------
# 7-day calendar renderer (Mon..Sun) with NO weekend items
# -----------------------------------------------------------
def _render_calendar_7day_skip_weekends(filtered_rows, target_month, current_user=None, only_mine=False):
    """
    Draw a 7-day calendar (Mon..Sun) but do not plot any project items on
    Saturday/Sunday. Weekends still display day numbers; their cells stay empty.
    """
    # Headers Mon..Sun
    st.markdown("#### Calendar")
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    header_cols = st.columns(7)
    for i, dn in enumerate(day_names):
        header_cols[i].markdown(f"**{dn}**")

    # Status colors
    status_colors = {
        "COMPLETE": "#006400",   # dark green
        "IN-PROGRESS": "#F2B705",
        "OVERDUE": "#8B0000",
        "Unknown": "#9E9E9E"
    }

    year = target_month.year
    month = target_month.month

    cal = calendar.Calendar(firstweekday=0)  # Monday=0
    weeks = cal.monthdatescalendar(year, month)  # list of weeks; each is 7 dates (Mon..Sun)

    # Map each day -> list of items, but NEVER index weekend days.
    by_day = {}
    for row in filtered_rows:
        theme_name    = row[1] or "Unknown"
        project_name  = row[3]
        registered_by = row[9] or "Unknown"
        status        = row[11] or "Unknown"

        if only_mine and current_user:
            if (row[9] or "Unknown") != current_user:
                continue

        start, end = _project_date_range(row)
        if not start and not end:
            continue
        if not start: start = end
        if not end:   end   = start

        # Add this project on each day in its span, but SKIP weekends entirely
        for d in pd.date_range(start=start, end=end, freq="D"):
            d = d.date()
            if d.weekday() >= 5:  # 5=Sat, 6=Sun => do not add items
                continue
            if d.year == year and d.month == month:
                by_day.setdefault(d, []).append({
                    "project": project_name,
                    "user": registered_by,
                    "status": status,
                    "theme": theme_name
                })

    # Render week rows (Mon..Sun). Weekend columns show no items by design.
    for week in weeks:
        cols = st.columns(7)
        for i, d in enumerate(week):
            with cols[i]:
                muted = d.month != month
                day_no = f"<span style='opacity:0.45;'>{d.day}</span>" if muted else f"<span>{d.day}</span>"
                st.markdown(f"<div style='font-weight:600; font-size:16px;'>{day_no}</div>", unsafe_allow_html=True)

                # Only show items for weekdays; weekends intentionally empty
                items = by_day.get(d, []) if d.weekday() < 5 else []
                if items:
                    max_items = 6
                    for item in items[:max_items]:
                        color = status_colors.get(item["status"], status_colors["Unknown"])
                        st.markdown(
                            f"""
                            <div style="display:flex; align-items:center; gap:6px; margin:1px 0;">
                                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{color};"></span>
                                <span style="font-size:12.5px;">{item['project']} <span style="opacity:0.55;">({item['user']})</span></span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    if len(items) > max_items:
                        st.markdown(
                            f"<div style='opacity:0.6; font-size:12px;'>+{len(items)-max_items} more…</div>",
                            unsafe_allow_html=True
                        )
                else:
                    # leave weekend cells empty; add small spacer for layout consistency
                    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------
# ANALYTICS → Calendar schedule (period optional)
# -----------------------------------------------------------
def show_analytics():

    st.title("Project Schedule (Calendar)")

    # Load once
    rows = get_all_projects()

    # ----- Periods -----
    # Use master periods if available; otherwise derive unique codes from rows.
    master_periods = get_all_periods()
    master_codes = [pcode for (_pid, pcode, _desc) in master_periods if pcode]

    if master_codes:
        period_choice = st.selectbox("Period", master_codes)
        period_filter = period_choice
    else:
        # Fallback: derive from project data; if still none, allow "All Periods"
        derived_codes = sorted({(r[2] or "") for r in rows if r[2]})
        period_choice = st.selectbox("Period", ["All Periods"] + derived_codes)
        period_filter = None if period_choice == "All Periods" else period_choice

    # ----- Themes (DB master keeps sequence consistent with FK) -----
    theme_rows = get_all_themes()            # [(id, theme_name), ...]
    theme_names = [tname for (_tid, tname) in theme_rows]
    theme_choice = st.selectbox("Theme", ["All Themes"] + theme_names)
    theme_filter = None if theme_choice == "All Themes" else theme_choice

    # ----- Users (registered_by at idx 9) -----
    users = sorted({(r[9] or "Unknown") for r in rows})
    user_multiselect = st.multiselect("Users (Registered By)", ["All Users"] + users, default=["All Users"])
    user_filters = None if ("All Users" in user_multiselect or len(user_multiselect) == 0) else set(user_multiselect)

    # Only my tasks (does not affect DB/KPIs; just filters the calendar)
    current_user = st.session_state.get("username", None)
    only_mine = st.toggle("Show only my tasks", value=False)

    st.write("---")

    # ----- Month navigation -----
    today = datetime.date.today()
    default_month = datetime.date(today.year, today.month, 1)

    nav1, nav2, nav3 = st.columns([0.16, 0.6, 0.24])
    with nav1:
        prev = st.button("◀ Previous month")
    with nav3:
        nxt = st.button("Next month ▶")

    if "calendar_month" not in st.session_state:
        st.session_state["calendar_month"] = default_month

    cur_month = st.session_state["calendar_month"]
    if prev:
        y, m = cur_month.year, cur_month.month - 1
        if m == 0:
            y -= 1; m = 12
        st.session_state["calendar_month"] = datetime.date(y, m, 1)
    if nxt:
        y, m = cur_month.year, cur_month.month + 1
        if m == 13:
            y += 1; m = 1
        st.session_state["calendar_month"] = datetime.date(y, m, 1)

    cur_month = st.session_state["calendar_month"]
    with nav2:
        st.markdown(
            f"<div style='text-align:center; font-weight:700; font-size:18px;'>{cur_month.strftime('%B %Y')}</div>",
            unsafe_allow_html=True
        )

    # ----- Apply filters to rows -----
    filtered = []
    for r in rows:
        theme_name     = r[1] or None      # theme_name (JOIN result)
        period_code    = r[2] or None
        registered_by  = r[9] or "Unknown"

        if period_filter is not None and period_code != period_filter:
            continue
        if theme_filter is not None and theme_name != theme_filter:
            continue
        if user_filters is not None and registered_by not in user_filters:
            continue

        filtered.append(r)

    # Small summary above calendar (task counts; not day-based)
    completed = overdue = inprogress = 0
    for r in filtered:
        status = r[11] or "Unknown"
        if status == "COMPLETE":
            completed += 1
        elif status == "OVERDUE":
            overdue += 1
        else:
            inprogress += 1

    total_filtered = completed + overdue + inprogress
    colS1, colS2, colS3, colS4 = st.columns(4)
    colS1.metric("Total", total_filtered)
    colS2.metric("Completed", completed)
    colS3.metric("In-Progress", inprogress)
    colS4.metric("Overdue", overdue)

    # ----- 7-day calendar, but never show items on Sat/Sun -----
    _render_calendar_7day_skip_weekends(
        filtered_rows=filtered,
        target_month=cur_month,
        current_user=current_user,
        only_mine=only_mine
    )
