import streamlit as st
import pandas as pd

from db.queries import (
    get_all_projects,
    search_projects,
    delete_project
)


# -----------------------------------------------------------
# LOAD FULL PROJECT TABLE INTO DATAFRAME
# -----------------------------------------------------------
def load_project_df(rows):
    """Convert DB rows to a pandas DataFrame for Streamlit."""
    data = []
    for row in rows:
        (
            project_id, theme_name, period_code, project_name,
            product_item, process_name, details, deadline, remark,
            registered_by, registered_on, status, kpi_value,
            created_at, updated_at
        ) = row

        data.append({
            "ID": project_id,
            "Theme": theme_name,
            "Period": period_code,
            "Project": project_name,
            "Product Item": product_item,
            "Process": process_name,
            "Deadline": deadline,
            "Status": status,
            "Registered By": registered_by,
            "KPI": kpi_value
        })

    return pd.DataFrame(data)


# -----------------------------------------------------------
# MAIN PROJECT PAGE
# -----------------------------------------------------------
def show_projects(username):
    st.title("Projects")
    st.caption(f"Logged in as: {username}")

    # -------------------------------------------------------
    # SEARCH BAR
    # -------------------------------------------------------
    search_keyword = st.text_input(
        "Search Project (name, process, theme...)",
        placeholder="Type keyword to search..."
    )

    # Load rows depending on search
    if search_keyword.strip() == "":
        rows = get_all_projects()
    else:
        rows = search_projects(search_keyword)

    df = load_project_df(rows)

    # -------------------------------------------------------
    # SHOW PROJECT TABLE
    # -------------------------------------------------------
    st.subheader("Project List")
    st.dataframe(df, width="stretch")

    # -------------------------------------------------------
    # SELECT PROJECT TO EDIT / DELETE
    # -------------------------------------------------------
    if len(df) > 0:
        selected_id = st.selectbox(
            "Select a project ID:",
            df["ID"].tolist()
        )
    else:
        selected_id = None
        st.warning("No project records available.")

    # -------------------------------------------------------
    # ACTION BUTTONS
    # -------------------------------------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Add New Project"):
            st.session_state.edit_mode = "add"
            st.session_state.edit_project_id = None
            st.session_state.page = "Project Form"
            st.rerun()

    with col2:
        if st.button("✏️ Edit Selected", disabled=(selected_id is None)):
            st.session_state.edit_mode = "edit"
            st.session_state.edit_project_id = selected_id
            st.session_state.page = "Project Form"
            st.rerun()

    with col3:
        if st.button("🗑 Delete Selected", disabled=(selected_id is None)):
            delete_project(selected_id)
            st.success(f"Project ID {selected_id} deleted.")
            st.rerun()