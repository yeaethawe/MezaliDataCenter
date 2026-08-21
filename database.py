import sqlite3
from datetime import datetime, timezone

file_path = "data.db"
# Connect to a file-based database (creates 'example.db' if it doesn't exist)
connection = sqlite3.connect(file_path)

# Create a cursor object to execute SQL commands
cursor = connection.cursor()

# Create a new table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        password TEXT NOT NULL
    )
""")

user_columns = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
if "profile_picture" not in user_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN profile_picture TEXT")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        img TEXT NOT NULL,
        price INTEGER NOT NULL,
        decryption TEXT NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS storage_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        original_name TEXT NOT NULL,
        stored_name TEXT NOT NULL UNIQUE,
        mime_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS storage_folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        parent_id INTEGER,
        UNIQUE (user_id, name),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (parent_id) REFERENCES storage_folders (id) ON DELETE CASCADE
    )
""")

folder_columns = {row[1] for row in cursor.execute("PRAGMA table_info(storage_folders)")}
if "parent_id" not in folder_columns:
    cursor.execute("ALTER TABLE storage_folders ADD COLUMN parent_id INTEGER REFERENCES storage_folders (id) ON DELETE CASCADE")

storage_columns = {row[1] for row in cursor.execute("PRAGMA table_info(storage_items)")}
if "folder_id" not in storage_columns:
    cursor.execute("ALTER TABLE storage_items ADD COLUMN folder_id INTEGER REFERENCES storage_folders (id) ON DELETE SET NULL")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_a_id INTEGER NOT NULL,
        user_b_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (user_a_id, user_b_id),
        FOREIGN KEY (user_a_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (user_b_id) REFERENCES users (id) ON DELETE CASCADE,
        CHECK (user_a_id < user_b_id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        body TEXT,
        storage_item_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE,
        FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (storage_item_id) REFERENCES storage_items (id) ON DELETE SET NULL,
        CHECK (body IS NOT NULL OR storage_item_id IS NOT NULL)
    )
""")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_storage_user ON storage_items (user_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at)")

# Commit changes to save them to the database file
connection.commit()
cursor.close()
connection.close()

def sql():
    connection = sqlite3.connect(file_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def add_user(name, email, password):
    try:
        with sql() as con:
            cursor = con.cursor()
            user_data = (name, email, password)
            cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", user_data)
            user_id = cursor.lastrowid
        print(f"User added successfully with name: {name}, email: {email}")
        return user_id
    except sqlite3.Error as e:
        print(f"We have caught an error {e}")
        return e

def add_product(name, img, price, decryption):
    try:
        with sql() as con:
            cursor = con.cursor()
            product_data = (name, img, price, decryption)
            cursor.execute("INSERT INTO products (name, img, price, decryption) VALUES (?,?,?,?)", product_data)
    except sqlite3.Error as e:
        print(f"We have caught an error {e}")
        return e
    
def get_all_users():
    with sql() as con:
        cursor = con.cursor()
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()

def get_all_products():
    with sql() as con:
        cursor = con.cursor()
        cursor.execute("SELECT * FROM products")
        return cursor.fetchall()

def get_user_by_id(id):
    with sql() as con:
        cursor = con.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?",(id,))
        return cursor.fetchall()

def get_product_by_id(id):
    with sql() as con:
        cursor = con.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?",(id,))
        return cursor.fetchall()


def update_username(name, email):
    with sql() as con:
        cursor = con.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE email = ?", (name, email))

def update_product(id, name, img, price, decryption):
    with sql() as con:
        cursor = con.cursor()
        cursor.execute("UPDATE products SET name = ?, img = ?, price = ?, decryption = ? WHERE id = ?",(name, img, price, decryption, id))

def delete_user(email):
    try:
        with sql() as con:
            cursor = con.cursor()
            cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    except sqlite3.Error as e:
        return e

def login_user(email, password):
    try:
        with sql() as con:
            cursor = con.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
            return cursor.fetchall()
    except sqlite3.Error as e:
        return e

def get_user_by_email(email):
    with sql() as con:
        return con.execute("SELECT id, name, email FROM users WHERE email = ?", (email,)).fetchone()

def get_user_by_id_safe(user_id):
    with sql() as con:
        return con.execute("SELECT id, name, email, profile_picture FROM users WHERE id = ?", (user_id,)).fetchone()

def update_profile_picture(user_id, stored_name):
    with sql() as con:
        con.execute("UPDATE users SET profile_picture = ? WHERE id = ?", (stored_name, user_id))

def get_or_create_storage_folder(user_id, name):
    with sql() as con:
        folder = con.execute("SELECT id FROM storage_folders WHERE user_id = ? AND name = ?", (user_id, name)).fetchone()
        if folder:
            return folder[0]
        cursor = con.execute(
            "INSERT INTO storage_folders (user_id, name, created_at) VALUES (?, ?, ?)",
            (user_id, name, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid
    
def update_user_name(user_id, name):
    with sql() as con:
        cursor = con.execute("UPDATE users SET name = ? WHERE id = ?", (name.strip(), user_id))
        return cursor.rowcount == 1

def change_user_password(user_id, current_password, new_password):
    with sql() as con:
        user = con.execute("SELECT password FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user or user[0] != current_password:
            return False
        con.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user_id))
        return True

def add_storage_item(user_id, original_name, stored_name, mime_type, size_bytes):
    with sql() as con:
        cursor = con.execute(
            "INSERT INTO storage_items (user_id, original_name, stored_name, mime_type, size_bytes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, original_name, stored_name, mime_type, size_bytes, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid

def get_storage_items(user_id):
    with sql() as con:
        return con.execute(
            "SELECT id, original_name, mime_type, size_bytes, created_at FROM storage_items WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

def get_storage_items_in_folder(user_id, folder_id=None):
    with sql() as con:
        if folder_id is None:
            return con.execute(
                "SELECT id, original_name, mime_type, size_bytes, created_at, folder_id FROM storage_items WHERE user_id = ? AND folder_id IS NULL ORDER BY original_name COLLATE NOCASE",
                (user_id,),
            ).fetchall()
        return con.execute(
            "SELECT id, original_name, mime_type, size_bytes, created_at, folder_id FROM storage_items WHERE user_id = ? AND folder_id = ? ORDER BY original_name COLLATE NOCASE",
            (user_id, folder_id),
        ).fetchall()

def get_storage_folders(user_id):
    with sql() as con:
        return con.execute("SELECT id, name, created_at, parent_id FROM storage_folders WHERE user_id = ? ORDER BY name COLLATE NOCASE", (user_id,)).fetchall()

def get_storage_folders_in_folder(user_id, parent_id=None):
    with sql() as con:
        if parent_id is None:
            return con.execute("SELECT id, name, created_at, parent_id FROM storage_folders WHERE user_id = ? AND parent_id IS NULL ORDER BY name COLLATE NOCASE", (user_id,)).fetchall()
        return con.execute("SELECT id, name, created_at, parent_id FROM storage_folders WHERE user_id = ? AND parent_id = ? ORDER BY name COLLATE NOCASE", (user_id, parent_id)).fetchall()

def add_storage_folder(user_id, name, parent_id=None):
    try:
        with sql() as con:
            cursor = con.execute(
                "INSERT INTO storage_folders (user_id, name, created_at, parent_id) VALUES (?, ?, ?, ?)",
                (user_id, name.strip(), datetime.now(timezone.utc).isoformat(), parent_id),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None

def get_storage_folder(folder_id, user_id):
    with sql() as con:
        return con.execute("SELECT id, name, parent_id FROM storage_folders WHERE id = ? AND user_id = ?", (folder_id, user_id)).fetchone()

def move_storage_folder(folder_id, user_id, parent_id):
    with sql() as con:
        if parent_id is not None:
            if parent_id == folder_id or not con.execute("SELECT 1 FROM storage_folders WHERE id = ? AND user_id = ?", (parent_id, user_id)).fetchone():
                return False
            descendant = con.execute(
                """WITH RECURSIVE children(id) AS (
                       SELECT id FROM storage_folders WHERE parent_id = ?
                       UNION ALL SELECT folders.id FROM storage_folders folders JOIN children ON folders.parent_id = children.id
                   ) SELECT 1 FROM children WHERE id = ?""",
                (folder_id, parent_id),
            ).fetchone()
            if descendant:
                return False
        cursor = con.execute("UPDATE storage_folders SET parent_id = ? WHERE id = ? AND user_id = ?", (parent_id, folder_id, user_id))
        return cursor.rowcount == 1

def delete_storage_folder(folder_id, user_id):
    with sql() as con:
        folder = con.execute("SELECT name FROM storage_folders WHERE id = ? AND user_id = ?", (folder_id, user_id)).fetchone()
        if not folder:
            return None
        con.execute("DELETE FROM storage_folders WHERE id = ? AND user_id = ?", (folder_id, user_id))
        return folder[0]

def rename_storage_item(item_id, user_id, name):
    with sql() as con:
        cursor = con.execute("UPDATE storage_items SET original_name = ? WHERE id = ? AND user_id = ?", (name.strip(), item_id, user_id))
        return cursor.rowcount == 1

def move_storage_item(item_id, user_id, folder_id):
    with sql() as con:
        if folder_id is not None and not con.execute("SELECT 1 FROM storage_folders WHERE id = ? AND user_id = ?", (folder_id, user_id)).fetchone():
            return False
        cursor = con.execute("UPDATE storage_items SET folder_id = ? WHERE id = ? AND user_id = ?", (folder_id, item_id, user_id))
        return cursor.rowcount == 1

def get_storage_usage(user_id):
    with sql() as con:
        return con.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM storage_items WHERE user_id = ?", (user_id,)).fetchone()[0]

def get_storage_item(item_id):
    with sql() as con:
        return con.execute("SELECT * FROM storage_items WHERE id = ?", (item_id,)).fetchone()

def delete_storage_item(item_id, user_id):
    with sql() as con:
        item = con.execute("SELECT stored_name FROM storage_items WHERE id = ? AND user_id = ?", (item_id, user_id)).fetchone()
        if not item:
            return None
        con.execute("DELETE FROM storage_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        return item[0]

def get_or_create_conversation(user_id, other_user_id):
    user_a, user_b = sorted((int(user_id), int(other_user_id)))
    if user_a == user_b:
        return None
    with sql() as con:
        conversation = con.execute(
            "SELECT id, user_a_id, user_b_id FROM conversations WHERE user_a_id = ? AND user_b_id = ?",
            (user_a, user_b),
        ).fetchone()
        if conversation:
            return conversation
        cursor = con.execute(
            "INSERT INTO conversations (user_a_id, user_b_id, created_at) VALUES (?, ?, ?)",
            (user_a, user_b, datetime.now(timezone.utc).isoformat()),
        )
        return (cursor.lastrowid, user_a, user_b)

def search_users(query, current_user_id):
    search_term = f"%{query.strip()}%"
    with sql() as con:
        return con.execute(
            """SELECT id, name, email FROM users
               WHERE id != ? AND (name LIKE ? OR email LIKE ?)
               ORDER BY name LIMIT 25""",
            (current_user_id, search_term, search_term),
        ).fetchall()

def get_user_conversations(user_id):
    with sql() as con:
        return con.execute(
            """SELECT conversations.id,
                      CASE WHEN conversations.user_a_id = ? THEN conversations.user_b_id ELSE conversations.user_a_id END,
                      users.name, users.email, messages.body, messages.created_at
               FROM conversations
               JOIN users ON users.id = CASE
                   WHEN conversations.user_a_id = ? THEN conversations.user_b_id
                   ELSE conversations.user_a_id END
               LEFT JOIN messages ON messages.id = (
                   SELECT latest.id FROM messages AS latest
                   WHERE latest.conversation_id = conversations.id
                   ORDER BY latest.created_at DESC, latest.id DESC LIMIT 1
               )
               WHERE conversations.user_a_id = ? OR conversations.user_b_id = ?
               ORDER BY COALESCE(messages.created_at, conversations.created_at) DESC""",
            (user_id, user_id, user_id, user_id),
        ).fetchall()

def get_conversation(conversation_id, user_id):
    with sql() as con:
        return con.execute(
            "SELECT id, user_a_id, user_b_id FROM conversations WHERE id = ? AND (user_a_id = ? OR user_b_id = ?)",
            (conversation_id, user_id, user_id),
        ).fetchone()

def get_messages(conversation_id, user_id):
    with sql() as con:
        return con.execute(
            """SELECT messages.id, messages.sender_id, users.name, messages.body,
                      messages.storage_item_id, storage_items.original_name,
                      storage_items.mime_type, messages.created_at,
                      users.profile_picture
               FROM messages JOIN users ON users.id = messages.sender_id
               LEFT JOIN storage_items ON storage_items.id = messages.storage_item_id
               WHERE messages.conversation_id = ? AND EXISTS (
                   SELECT 1 FROM conversations WHERE id = ? AND (user_a_id = ? OR user_b_id = ?)
               ) ORDER BY messages.created_at""",
            (conversation_id, conversation_id, user_id, user_id),
        ).fetchall()

def add_message(conversation_id, sender_id, body=None, storage_item_id=None):
    with sql() as con:
        if not con.execute(
            "SELECT 1 FROM conversations WHERE id = ? AND (user_a_id = ? OR user_b_id = ?)",
            (conversation_id, sender_id, sender_id),
        ).fetchone():
            return None
        cursor = con.execute(
            "INSERT INTO messages (conversation_id, sender_id, body, storage_item_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, sender_id, body, storage_item_id, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid

def can_access_shared_item(item_id, user_id, conversation_id):
    with sql() as con:
        return con.execute(
            """SELECT storage_items.* FROM storage_items
               JOIN messages ON messages.storage_item_id = storage_items.id
               JOIN conversations ON conversations.id = messages.conversation_id
               WHERE storage_items.id = ? AND messages.conversation_id = ?
                 AND (conversations.user_a_id = ? OR conversations.user_b_id = ?)""",
            (item_id, conversation_id, user_id, user_id),
        ).fetchone()

def delete_product(id):
    try:
        with sql() as con:
            cursor = con.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (id,))
    except sqlite3.Error as e:
        return e
