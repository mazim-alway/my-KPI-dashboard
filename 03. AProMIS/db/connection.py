import sqlite3
import configparser
import os
from pathlib import Path


def get_database_path():
    """
    Safe loader for database path.
    Automatically repairs config.ini if DATABASE section or db_path key is missing.
    """
    config = configparser.ConfigParser()

    # If file missing -> recreate minimal config
    if not os.path.exists("config.ini"):
        with open("config.ini", "w") as f:
            f.write("[DATABASE]\ndb_path=mis.db\n[PIC]\n")
        config.read("config.ini")
    else:
        config.read("config.ini")

    # Ensure DATABASE section exists
    if "DATABASE" not in config:
        config["DATABASE"] = {"db_path": "mis.db"}

    # Ensure db_path exists
    if "db_path" not in config["DATABASE"]:
        config["DATABASE"]["db_path"] = "mis.db"

    # Save repaired config.ini
    with open("config.ini", "w") as f:
        config.write(f)

    # Now safely read db_path
    raw_path = config["DATABASE"]["db_path"].strip()

    # Normalize Windows UNC or local path
    db_path = os.path.normpath(raw_path)
    db_dir = os.path.dirname(db_path)

    # Validate folder
    if db_dir and not Path(db_dir).exists():
        raise FileNotFoundError(
            f"Shared folder not found:\n{db_dir}\n\n"
            "Please confirm your network path is correct or online."
        )

    return db_path


def initialize_database():
    """
    Creates database + tables if mis.db does not exist.
    Uses schema.sql file to build tables.
    """
    db_path = get_database_path()

    # If DB does not exist → create new SQLite database
    if not os.path.exists(db_path):
        print("🔧 Database not found — creating new mis.db ...")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Load schema from SQL file
        if not os.path.exists("db/schema.sql"):
            raise FileNotFoundError("schema.sql missing in /db folder.")

        with open("db/schema.sql", "r", encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()

        cursor.executescript(schema_sql)
        conn.commit()
        conn.close()

        print("✅ Database created successfully using schema.sql")
    else:
        # Optional: remove print to avoid repetition
        # print("✔ Database exists — no need to create.")
        pass


def get_connection():
    """
    Opens a safe SQLite connection with multi-user timeout.
    """
    db_path = get_database_path()

    # Multi-user safe timeout = 10 seconds
    conn = sqlite3.connect(
        db_path,
        timeout=10,
        check_same_thread=False  # Allows use in PySide threads
    )

    return conn