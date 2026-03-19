import streamlit as st
import datetime
from db.queries import (
    get_all_projects,
    get_all_themes,
    add_project,
    update_project
)


# -----------------------------------------------------------
# Load project for editing (returns a dict with display fields)
# -----------------------------------------------------------
def load_existing_project(project_id):
    rows = get_all_projects()
    for row in rows:
        if row[0] == project_id:
            return {
                "theme_name":   row[1],   # joined from themes
                "project_name": row[3],
                "product_item": row[4],
                "process_name": row[5],
                "deadline":     row[7],
                "status":       row[11],
            }
    return None


# -----------------------------------------------------------
# MAIN ADD/EDIT PROJECT FORM
# -----------------------------------------------------------
def show_project_form(username):

    st.title("Add / Edit Project")

    mode = st.session_state.get("edit_mode")
    project_id = st.session_state.get("edit_project_id")

    if mode not in ["add", "edit"]:
        st.error("Form opened without a valid mode. Redirecting to Projects.")
        st.session_state.page = "Projects"
        st.rerun()

    if mode == "edit" and project_id is None:
        st.error("Edit mode missing project ID. Redirecting to Projects.")
        st.session_state.page = "Projects"
        st.rerun()

    # -------------------------------------------------------
    # Theme master from DB (id, name) -> map name->id
    # -------------------------------------------------------
    themes = get_all_themes()  # [(id, theme_name), ...]
    if not themes:
        st.error("No themes found in database. Please restart the app to seed defaults.")
        return

    theme_map = {t[1]: t[0] for t in themes}     # name -> id
    theme_list = list(theme_map.keys())          # ordered by id ASC (as returned)

    # Defaults
    default = {
        "theme_name": theme_list[0],
        "project_name": "",
        "product_item": "",
        "process_name": "",
        "deadline": datetime.date.today(),
        "status": "IN-PROGRESS",
    }

    # Load project values for edit
    if mode == "edit":
        data = load_existing_project(project_id)
        if data:
            # Convert deadline safely
            if data["deadline"]:
                try:
                    default["deadline"] = datetime.date.fromisoformat(str(data["deadline"]))
                except Exception:
                    pass
            default.update(data)
        else:
            st.error("Project not found. Redirecting…")
            st.session_state.page = "Projects"
            st.rerun()

    # Safe index for theme selection
    theme_index = theme_list.index(default["theme_name"]) if default["theme_name"] in theme_list else 0

    # -------------------------------------------------------
    # FORM UI
    # -------------------------------------------------------
    with st.form("project_form"):
        theme_name = st.selectbox("Theme", theme_list, index=theme_index)
        project_name = st.text_input("Project Name", default["project_name"])
        product_item = st.text_input("Product Item", default["product_item"])
        process_name = st.text_input("Process", default["process_name"])
        deadline = st.date_input("Deadline", default["deadline"])
        status = st.selectbox(
            "Status",
            ["COMPLETE", "IN-PROGRESS", "OVERDUE"],
            index=["COMPLETE", "IN-PROGRESS", "OVERDUE"].index(default["status"])
        )

        submitted = st.form_submit_button("Save Project")

    # -------------------------------------------------------
    # SAVE HANDLER
    # -------------------------------------------------------
    if submitted:
        # Validate
        if not project_name.strip():
            st.warning("Project name is required.")
            return

        theme_id = theme_map[theme_name]         # ✅ Save FK
        period_id = None                         # (Optional) extend later when you add period picker
        deadline_str = deadline.strftime("%Y-%m-%d")

        if mode == "add":
            add_project(
                theme_id, period_id,
                project_name, product_item, process_name,
                None,                  # details
                deadline_str,
                None,                  # remark
                username, None,        # registered_by / on
                status, None           # kpi_value
            )
            st.success("Project added successfully.")
        else:
            update_project(
                project_id, theme_id, period_id,
                project_name, product_item, process_name,
                None,                  # details
                deadline_str,
                None,                  # remark
                status, None
            )
            st.success("Project updated successfully.")

        # Go back to Projects
        st.session_state.page = "Projects"
        st.rerun()