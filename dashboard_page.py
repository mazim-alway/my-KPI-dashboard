import streamlit as st
import plotly.graph_objects as go
import configparser
import os
import datetime

#from plotly.io import templates

from db.queries import (
    get_all_projects,
    get_all_themes,
)

# -----------------------------------------------------------
# Helper: Load & Save PIC info
# -----------------------------------------------------------
def load_pic_info():
    config = configparser.ConfigParser()
    config.read("config.ini")

    if "PIC" not in config:
        config["PIC"] = {}

    return {
        "name": config["PIC"].get("name", ""),
        "email": config["PIC"].get("email", ""),
        "job_grade": config["PIC"].get("job_grade", ""),
        "expertise": config["PIC"].get("expertise", ""),
        "education": config["PIC"].get("education", ""),
        "photo_path": config["PIC"].get("photo_path", "assets/pic.png"),
    }


def save_pic_info(pic_dict):
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Preserve DATABASE section so DB path doesn't get lost
    if "DATABASE" not in config:
        config["DATABASE"] = {"db_path": "mis.db"}

    config["PIC"] = pic_dict

    with open("config.ini", "w") as f:
        config.write(f)


# -----------------------------------------------------------
# Helper: Score classification (color + label)
# -----------------------------------------------------------
def classify_score(score: float):
    """
    Returns (label, color_hex) based on score range.
    """
    if score <= 4.0:
        return "Very Poor", "#8B0000"   # dark red
    elif score <= 6.0:
        return "Poor", "#FF8C00"        # orange
    elif score <= 7.5:
        return "Average", "#FFD700"     # yellow
    elif score <= 8.5:
        return "Good", "#90EE90"        # light green
    else:
        return "Excellent", "#006400"   # dark green


# -----------------------------------------------------------
# MAIN DASHBOARD PAGE
# -----------------------------------------------------------
def show_dashboard(username):
    st.markdown(
        f"<h1 style='color:#D32F2F; font-size:42px;'>Dashboard — Welcome, {username}</h1>",
        unsafe_allow_html=True
    )

    pic = load_pic_info()
    if "edit_pic" not in st.session_state:
        st.session_state.edit_pic = False

    left, right = st.columns([1.3, 3])


    # -------------------------------------------------------
    # LEFT : PIC INFORMATION
    # -------------------------------------------------------
    with left:
        st.subheader("PIC Information")

        with st.container(border=True):

            if not st.session_state.edit_pic:
                st.write(f"**Name:** {pic['name']}")
                st.write(f"**Email:** {pic['email']}")
                st.write(f"**Job Grade:** {pic['job_grade']}")
                st.write("**Expertise:**")
                st.write(pic["expertise"])
                st.write("**Education:**")
                st.write(pic["education"])

                if os.path.exists(pic["photo_path"]):
                    st.image(pic["photo_path"], width=200)

                if st.button("✏️ Edit PIC Info", use_container_width=True):
                    st.session_state.edit_pic = True

            else:
                new_pic = {}
                new_pic["name"] = st.text_input("Name", pic["name"])
                new_pic["email"] = st.text_input("Email", pic["email"])
                new_pic["job_grade"] = st.text_input("Job Grade", pic["job_grade"])
                new_pic["expertise"] = st.text_area("Expertise", pic["expertise"])
                new_pic["education"] = st.text_area("Education", pic["education"])

                st.write("### Upload New PIC Photo")
                uploaded_photo = st.file_uploader(
                    "Drag & drop or click to upload",
                    type=["png", "jpg", "jpeg"],
                    accept_multiple_files=False
                )

                if uploaded_photo:
                    save_path = "assets/pic.png"
                    with open(save_path, "wb") as f:
                        f.write(uploaded_photo.getbuffer())
                    new_pic["photo_path"] = save_path
                else:
                    new_pic["photo_path"] = pic["photo_path"]

                cc1, cc2 = st.columns(2)

                with cc1:
                    if st.button("💾 Save", use_container_width=True):
                        save_pic_info(new_pic)
                        st.session_state.edit_pic = False
                        st.success("PIC Information Updated.")
                        st.rerun()

                with cc2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.edit_pic = False
                        st.rerun()

    # -------------------------------------------------------
    # RIGHT : Task Completion Rate (weekly overdue penalty)
    #         VISUAL: Completed vs Others (requested)
    # -------------------------------------------------------
    with right:

        st.subheader("Task Completion Rate")

        rows = get_all_projects()

        total = len(rows)
        completed = overdue = inprogress = 0
        today = datetime.date.today()
        overdue_weeks_total = 0  # sum only for rows flagged as OVERDUE

        for row in rows:
            # get_all_projects() schema (JOIN):
            # 0 id, 1 theme_name, 2 period_code, 3 project_name,
            # 4 product_item, 5 process_name, 6 details, 7 deadline,
            # 8 remark, 9 registered_by, 10 registered_on, 11 status,
            # 12 kpi_value, 13 created_at, 14 updated_at
            status = row[11]
            deadline_raw = row[7]

            # Weekly overdue (only penalize rows marked OVERDUE)
            try:
                deadline_date = datetime.date.fromisoformat(str(deadline_raw)) if deadline_raw else today
            except Exception:
                deadline_date = today

            days_diff = (today - deadline_date).days
            weeks_overdue = max(0, days_diff // 7)

            if status == "COMPLETE":
                completed += 1
            elif status == "OVERDUE":
                overdue += 1
                overdue_weeks_total += weeks_overdue
            else:
                inprogress += 1

        # Remaining (not used in donut but kept for logic completeness)
        remaining = total - (completed + overdue + inprogress)
        if remaining < 0:
            remaining = 0

        denom = total if total > 0 else 1
        completion_rate = completed / denom

        # Score scale 0.0–10.0 with weekly penalty
        task_score = (completion_rate * 10) - (overdue_weeks_total * 0.5)
        task_score = max(0.0, min(10.0, task_score))

        score_label, score_color = classify_score(task_score)

        # KPI counters
        kc1, kc2, kc3, kc4 = st.columns(4)
        kc1.metric("Total Tasks", total)
        kc2.metric("Completed", completed)
        kc3.metric("In-Progress", inprogress)
        kc4.metric("Overdue", overdue)

        # ----- VISUAL: Completed vs Others -----
        others = (inprogress + overdue) + max(0, remaining)

        # Fallback to faint ring to keep annotation visible
        vals = [completed, others]
        if completed == 0 and others == 0:
            vals = [0, 1]

        fig_task = go.Figure(data=[go.Pie(
            labels=["Completed", "In-progress"],
            values=vals,
            hole=0.60,
            marker=dict(
                colors=[
                    score_color,  # completed uses classification color
                    "#E0E0E0"     # blurred "Others"
                ],
                line=dict(color="#FFFFFF", width=2)
            ),
            textinfo="none",
            sort=False
        )])

        # Score & label inside donut
        fig_task.add_annotation(
            text=f"{task_score:.2f}",
            x=0.5, y=0.52,
            font=dict(size=36, color=score_color, family="Arial Black"),
            showarrow=False
        )
        fig_task.add_annotation(
            text=f"{score_label}",
            x=0.5, y=0.40,
            font=dict(size=14, color=score_color),
            showarrow=False
        )

        fig_task.update_layout(
            title="",
            title_x=0.5,
            height=520,
            showlegend=True,
            legend=dict(orientation="v", yanchor="top", y=0.98, xanchor="right", x=0.98)
        )

        st.plotly_chart(fig_task, width="stretch")
        st.write("---")

    # -----------------------------------------------------------
    # THEME KPI — Dropdown + weekly overdue
    # VISUAL: Completed vs Others (requested)
    # -----------------------------------------------------------
    st.subheader("Theme KPI Overview")

    theme_rows = get_all_themes()
    theme_list = [tname for (_tid, tname) in theme_rows]

    selected_theme = st.selectbox(
        "Select Theme to View:",
        theme_list if theme_list else ["(No themes)"]
    )
    if not theme_list:
        st.info("No themes found in database. Please restart app to seed default themes.")
        st.stop()

    t_completed = t_overdue = t_inprogress = t_total = 0
    t_overdue_weeks = 0

    today = datetime.date.today()
    rows = get_all_projects()

    for row in rows:
        theme_nm   = row[1]
        status     = row[11]
        deadline   = row[7]

        if theme_nm is None or theme_nm != selected_theme:
            continue

        t_total += 1

        # Overdue weeks only for rows marked OVERDUE
        try:
            ddate = datetime.date.fromisoformat(str(deadline)) if deadline else today
        except Exception:
            ddate = today

        overdue_days = (today - ddate).days
        weeks = max(0, overdue_days // 7)

        if status == "COMPLETE":
            t_completed += 1
        elif status == "OVERDUE":
            t_overdue += 1
            t_overdue_weeks += weeks
        else:
            t_inprogress += 1

    t_remaining = t_total - (t_completed + t_overdue + t_inprogress)
    if t_remaining < 0:
        t_remaining = 0

    denom_t = t_total if t_total > 0 else 1
    t_completion_rate = t_completed / denom_t
    t_score = (t_completion_rate * 10) - (t_overdue_weeks * 0.5)
    t_score = max(0.0, min(10.0, t_score))

    label, color = classify_score(t_score)

    # ----- VISUAL: Completed vs Others -----
    t_others = (t_inprogress + t_overdue) + max(0, t_remaining)
    vals_theme = [t_completed, t_others]
    if t_completed == 0 and t_others == 0:
        vals_theme = [0, 1]

    fig_theme = go.Figure(data=[go.Pie(
        labels=["Completed", "In-progress"],
        values=vals_theme,
        hole=0.60,
        marker=dict(
            colors=[
                color,     # completed slice uses score classification color
                "#E0E0E0"  # blurred "Others"
            ],
            line=dict(color="#FFFFFF", width=2)
        ),
        textinfo="none",
        sort=False
    )])

    # Score & label inside donut
    fig_theme.add_annotation(
        text=f"{t_score:.2f}",
        x=0.5, y=0.52,
        font=dict(size=36, color=color, family="Arial Black"),
        showarrow=False
    )
    fig_theme.add_annotation(
        text=f"{label}",
        x=0.5, y=0.40,
        font=dict(size=14, color=color),
        showarrow=False
    )

    fig_theme.update_layout(
        title=f"{selected_theme}",
        title_x=0.5,
        height=520,
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=0.98, xanchor="right", x=0.98)
    )

    st.plotly_chart(fig_theme, width="stretch")

    # -----------------------------------------------------------
    # TOP 5 DELAYED TASKS (most weeks overdue)
    # -----------------------------------------------------------
    st.subheader("Top 5 Delayed Tasks (Most Overdue Weeks)")

    delayed_list = []
    for row in rows:
        project_id  = row[0]
        theme_nm    = row[1]
        project_nm  = row[3]
        deadline    = row[7]
        status      = row[11]

        try:
            ddate = datetime.date.fromisoformat(str(deadline)) if deadline else today
        except Exception:
            ddate = today

        overdue_days = (today - ddate).days
        overdue_weeks = max(0, overdue_days // 7)

        # Consider delayed = past-deadline and not complete
        if overdue_weeks > 0 and status != "COMPLETE":
            delayed_list.append({
                "Project": project_nm,
                "Theme": theme_nm,
                "Deadline": deadline,
                "Weeks Overdue": overdue_weeks,
                "Status": status
            })

    delayed_list = sorted(delayed_list, key=lambda x: x["Weeks Overdue"], reverse=True)[:5]

    if delayed_list:
        st.table(delayed_list)
    else:
        st.info("No delayed tasks found.")
