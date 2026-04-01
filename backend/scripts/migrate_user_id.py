import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "database.db")

TABLES_TO_ADD_USER_ID = [
    "task", "tasklog",
    "rssgroup", "rssfeed", "rssarticle",
    "channel", "channelmessage",
    "chatsession", "chatmessage",
    "agent_store", "skill_store", "skill_install_record", "skill_dependency",
    "articlenote", "articlesummary",
    "userprofile", "userprofilehistory",
    "contentrepo",
    "planmilestone", "plantask",
    "cardversion"
]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Check Admin User
        cursor.execute("SELECT id FROM user WHERE id = 1")
        admin_user = cursor.fetchone()
        if not admin_user:
            print("Admin user (id=1) not found in 'user' table. Creating one...")
            cursor.execute("INSERT INTO user (id, username, email, hashed_password, is_active, is_superuser) VALUES (1, 'admin', 'admin@example.com', 'dummy', 1, 1)")
            conn.commit()
            print("Admin user created.")

        # 2. Rename columns
        # Check if uploader_id exists in attachment
        cursor.execute("PRAGMA table_info(attachment)")
        attachment_columns = [info[1] for info in cursor.fetchall()]
        if "uploader_id" in attachment_columns:
            print("Renaming 'uploader_id' to 'user_id' in 'attachment' table...")
            cursor.execute("ALTER TABLE attachment RENAME COLUMN uploader_id TO user_id")
            print("Renamed in attachment.")
        elif "user_id" in attachment_columns:
            print("'user_id' already exists in 'attachment'.")

        # Check if creator_id exists in card
        cursor.execute("PRAGMA table_info(card)")
        card_columns = [info[1] for info in cursor.fetchall()]
        if "creator_id" in card_columns:
            print("Renaming 'creator_id' to 'user_id' in 'card' table...")
            cursor.execute("ALTER TABLE card RENAME COLUMN creator_id TO user_id")
            print("Renamed in card.")
        elif "user_id" in card_columns:
            print("'user_id' already exists in 'card'.")

        # 3. Add user_id to other tables
        for table in TABLES_TO_ADD_USER_ID:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            if not columns:
                print(f"Table '{table}' does not exist, skipping.")
                continue

            if "user_id" not in columns:
                print(f"Adding 'user_id' column to '{table}' table...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES user(id)")
                print(f"Added to {table}.")
            else:
                print(f"'user_id' already exists in '{table}'.")

        # 4. Refresh historical data
        all_tables_to_update = TABLES_TO_ADD_USER_ID + ["attachment", "card"]
        for table in all_tables_to_update:
            cursor.execute(f"PRAGMA table_info({table})")
            if cursor.fetchall():
                cursor.execute(f"UPDATE {table} SET user_id = 1 WHERE user_id IS NULL")
                updated_rows = cursor.rowcount
                if updated_rows > 0:
                    print(f"Updated {updated_rows} rows in '{table}' to set user_id = 1.")

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
