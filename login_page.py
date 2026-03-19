import streamlit as st
from db.connection import get_connection


# -----------------------------------------------------------
# LOAD USERS FROM DATABASE
# -----------------------------------------------------------
def load_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users ORDER BY username;")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]


# -----------------------------------------------------------
# ADD NEW USER TO DATABASE
# -----------------------------------------------------------
def add_new_user(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users (username, display_name)
        VALUES (?, ?)
    """, (username, username))
    conn.commit()
    conn.close()


# -----------------------------------------------------------
# STREAMLIT LOGIN PAGE
# -----------------------------------------------------------
def show_login():
    st.title("APro-MIS KPI System")
    st.subheader("Login")

    # Load users from DB
    users = load_users()

    # Session toggle: existing user vs new user
    if "new_user_mode" not in st.session_state:
        st.session_state.new_user_mode = False

    # Toggle button
    if st.button(
        "Add New User" if not st.session_state.new_user_mode else "Back to User List"
    ):
        st.session_state.new_user_mode = not st.session_state.new_user_mode

    st.write("---")

    # -----------------------------------------------------------
    # NEW USER MODE
    # -----------------------------------------------------------
    if st.session_state.new_user_mode:
        username = st.text_input("Enter new username:")

        if st.button("Create User & Login"):
            username = username.strip()

            if not username:
                st.warning("Please enter a valid username.")
                return

            add_new_user(username)
            st.success(f"User '{username}' created successfully!")

            # Login immediately
            st.session_state.username = username
            st.session_state.page = "Dashboard"
            st.rerun()

    # -----------------------------------------------------------
    # NORMAL LOGIN MODE
    # -----------------------------------------------------------
    else:
        if len(users) == 0:
            st.warning("No users found. Please add a new user.")
            return

        selected_user = st.selectbox("Select User:", users)

        if st.button("Login"):
            st.session_state.username = selected_user
            st.session_state.page = "Dashboard"
            st.rerun()