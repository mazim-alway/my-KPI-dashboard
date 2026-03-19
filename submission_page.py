import streamlit as st
import os
import csv
import datetime
import pandas as pd
from db.queries import get_all_projects, update_project_status, log_status_change_safe

SUBMIT_DIR = "assets/submissions"
LOG_PATH   = os.path.join(SUBMIT_DIR, "submissions_log.csv")


def _ensure_paths():
    os.makedirs(SUBMIT_DIR, exist_ok=True)
    if not os.path.exists(LOG_PATH):
        # create CSV with headers
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "username", "project_id", "project_name",
                "theme_name", "period_code", "status", "file_path", "remarks"
            ])


def _append_log(row):
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def _load_log_df():
    if not os.path.exists(LOG_PATH):
        return pd.DataFrame(columns=[
            "timestamp", "username", "project_id", "project_name",
            "theme_name", "period_code", "status", "file_path", "remarks"
        ])
    try:
        return pd.read_csv(LOG_PATH)
    except Exception:
        return pd.DataFrame(columns=[
            "timestamp", "username", "project_id", "project_name",
            "theme_name", "period_code", "status", "file_path", "remarks"
        ])


def show_submission(username):
    st.title("Submission")

    _ensure_paths()

    # Load projects once
    rows = get_all_projects()

    # ---- Filters ----
    statuses = ["All", "IN-PROGRESS", "OVERDUE", "COMPLETE"]
    c1, c2 = st.columns([1.2, 1.8])
    with c1:
        status_filter = st.selectbox("Filter by Status", statuses, index=0)
    with c2:
        search = st.text_input("Search Project", placeholder="Type to filter by project name…")

    # Build dataframe for selection
    data = []
    for r in rows:
        # r: 0 id, 1 theme_name, 2 period_code, 3 project_name, 4 product_item,
        #    5 process_name, 6 details, 7 deadline, 8 remark, 9 registered_by,
        #    10 registered_on, 11 status, 12 kpi_value, 13 created_at, 14 updated_at
        data.append({
            "ID": r[0],
            "Theme": r[1],
            "Period": r[2],
            "Project": r[3],
            "Status": r[11],
            "Registered By": r[9],
            "Deadline": r[7]
        })

    df = pd.DataFrame(data)

    # Apply filters locally
    if status_filter != "All":
        df = df[df["Status"] == status_filter]
    if search.strip():
        s = search.lower()
        df = df[df["Project"].str.lower().str.contains(s, na=False)]

    # Display list
    st.subheader("Project List")
    st.dataframe(df, width="stretch", height=360)

    selected_id = None
    if not df.empty:
        selected_id = st.selectbox("Select a Project ID to submit:", df["ID"].tolist())

    st.write("---")
    st.subheader("Submit Artifacts")

    if selected_id is None:
        st.info("Select a project above to submit files.")
        return

    # Find current row for selected project
    row = next((r for r in rows if r[0] == selected_id), None)
    if row is None:
        st.error("Selected project not found.")
        return

    st.markdown(f"**Project:** {row[3]}  \n**Theme:** {row[1]}  \n**Period:** {row[2]}  \n**Status:** {row[11]}")

    uploaded_files = st.file_uploader(
        "Attach files (drawings, images, reports, etc.)",
        type=["pdf", "png", "jpg", "jpeg", "xlsx", "xls", "csv", "docx", "pptx"],
        accept_multiple_files=True
    )
    remarks = st.text_area("Remarks", placeholder="Short note about this submission")

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Submit"):
            # Require at least a file or remarks
            if not uploaded_files and not remarks.strip():
                st.warning("Please attach at least one file or add remarks.")
                return

            # Save each file in /assets/submissions/<projectID>_<timestamp>_<filename>
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_paths = []
            for f in uploaded_files or []:
                safe_name = f"{selected_id}_{ts}_{f.name.replace(' ', '_')}"
                dest = os.path.join(SUBMIT_DIR, safe_name)
                with open(dest, "wb") as out:
                    out.write(f.getbuffer())
                saved_paths.append(dest)

            # Log the submission (CSV trail)
            _append_log([
                datetime.datetime.now().isoformat(),
                username,
                selected_id,
                row[3],   # project_name
                row[1],   # theme_name
                row[2],   # period_code
                row[11],  # current status
                ";".join(saved_paths),
                remarks.strip()
            ])

            # ---- NEW: auto-mark COMPLETE if currently IN-PROGRESS or OVERDUE ----
            old_status = (row[11] or "").upper()
            if old_status in ("IN-PROGRESS", "OVERDUE"):
                update_project_status(selected_id, "COMPLETE")
                log_status_change_safe(selected_id, old_status, "COMPLETE", changed_by=username)
                st.success(f"Submission recorded and status updated: {old_status} → COMPLETE")
            else:
                st.success("Submission recorded.")

            st.rerun()

    with colB:
        if st.button("View Submission Log"):
            log_df = _load_log_df()
            st.dataframe(log_df.sort_values("timestamp", ascending=False), width="stretch", height=360)
            st.download_button(
                "⬇ Download Submission Log (CSV)",
                data=log_df.to_csv(index=False).encode("utf-8"),
                file_name="submissions_log.csv",
                mime="text/csv"
            )