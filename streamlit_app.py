import streamlit as st
from db.connection import initialize_database

# Import pages
from login_page import show_login
from dashboard_page import show_dashboard
from projects_page import show_projects
from project_form_page import show_project_form
from analytics_page import show_analytics
from publish_page import show_publish
from settings_page import show_settings
from submission_page import show_submission  # keep your submission page

# -----------------------------------------------------------
# Initialize session state
# -----------------------------------------------------------
def init_session():
    if "username" not in st.session_state:
        st.session_state.username = None

    # keep "Project Form" programmatic route
    if "page" not in st.session_state:
        st.session_state.page = "Login"

    # structured navigation
    if "nav_section" not in st.session_state:
        st.session_state.nav_section = "Dashboard"

    if "projects_tab" not in st.session_state:
        st.session_state.projects_tab = "Registration"

    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = None
    if "edit_project_id" not in st.session_state:
        st.session_state.edit_project_id = None


# -----------------------------------------------------------
# Router
# -----------------------------------------------------------
def route():
    # login first
    if st.session_state.username is None:
        show_login()
        return

    # programmatic Project Form
    if st.session_state.page == "Project Form":
        show_project_form(st.session_state.username)
        return

    # Sidebar navigation
    with st.sidebar:
        st.title("Menu")
        st.selectbox(
            "Go to",
            ["Dashboard", "Projects", "Calendar", "Research Paper", "Settings"],  # <- exact label
            key="nav_section"
        )

        if st.session_state.nav_section == "Projects":
            st.selectbox(
                "Projects",
                ["Registration", "Submission"],
                key="projects_tab"
            )
            

    # Render sections
    if st.session_state.nav_section == "Dashboard":
        show_dashboard(st.session_state.username)

    elif st.session_state.nav_section == "Projects":
        if st.session_state.projects_tab == "Registration":
            show_projects(st.session_state.username)
        else:
            show_submission(st.session_state.username)

    elif st.session_state.nav_section == "Calendar":
        show_analytics()

    elif st.session_state.nav_section == "Research Paper":
        show_publish(st.session_state.username)  # <- pass username

    elif st.session_state.nav_section == "Settings":
        show_settings()


# -----------------------------------------------------------
def main():
    st.set_page_config(page_title="APro-MIS", layout="wide")
    initialize_database()
    init_session()
    route()


if __name__ == "__main__":
    main()
