import streamlit as st
import configparser
import os


# -----------------------------------------------------------
# Load settings from config.ini
# -----------------------------------------------------------
def load_settings():
    config = configparser.ConfigParser()
    config.read("config.ini")

    try:
        return config["DATABASE"]["db_path"]
    except:
        return ""


# -----------------------------------------------------------
# Save settings back to config.ini
# -----------------------------------------------------------
def save_settings(db_path):
    if not db_path:
        st.warning("Database path cannot be empty.")
        return False

    # Validate folder existence if it's a file path
    folder = os.path.dirname(db_path)
    if folder and not os.path.exists(folder):
        st.error(f"Folder does not exist:\n{folder}")
        return False

    config = configparser.ConfigParser()
    config["DATABASE"] = {"db_path": db_path}

    with open("config.ini", "w") as f:
        config.write(f)

    st.success("Settings updated successfully.")
    return True


# -----------------------------------------------------------
# SETTINGS PAGE UI
# -----------------------------------------------------------
def show_settings():
    st.title("Application Settings")
    st.write("Manage application configuration values stored in **config.ini**.")

    st.write("---")

    # Load current value
    current_path = load_settings()

    st.subheader("Database Path")

    db_path = st.text_input(
        "Shared Database Path",
        value=current_path,
        placeholder="Enter path to your SQLite .db file"
    )

    st.caption("💡 You may also upload a database file below to replace the current one.")

    uploaded_db = st.file_uploader("Upload SQLite .db file", type=["db"])

    if uploaded_db:
        # Save uploaded DB file into working directory
        save_path = os.path.join("uploaded_database.db")
        with open(save_path, "wb") as f:
            f.write(uploaded_db.getbuffer())

        st.success(f"Uploaded DB saved to: {save_path}")
        db_path = save_path  # Auto-fill new path

    st.write("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Settings"):
            save_settings(db_path)

    with col2:
        if st.button("🔄 Reload"):
            st.experimental_rerun()

    st.write("---")
    st.info("Changes take effect immediately after saving.")