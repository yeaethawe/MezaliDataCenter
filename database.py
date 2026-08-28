import hashlib
import os
import secrets
import sqlite3
import string
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
if "role" not in user_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
if "locked" not in user_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN locked INTEGER NOT NULL DEFAULT 0")
if "admin_upgrade_key" not in user_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN admin_upgrade_key TEXT")
if "created_at" not in user_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
if "public_share_id" not in user_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN public_share_id TEXT")
cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_public_share_id ON users (public_share_id)")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        reference_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL,
        dismissed INTEGER NOT NULL DEFAULT 0
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_hash TEXT NOT NULL UNIQUE,
        used_by INTEGER,
        used_at TEXT,
        FOREIGN KEY (used_by) REFERENCES users (id) ON DELETE SET NULL
    )
""")

def _hash_admin_key(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

if cursor.execute("SELECT COUNT(*) FROM admin_keys").fetchone()[0] == 0:
    alphabet = string.ascii_letters + string.digits
    generated_keys = []
    for _ in range(12):
        key = "".join(secrets.choice(alphabet) for _ in range(16))
        generated_keys.append(key)
        cursor.execute("INSERT INTO admin_keys (key_hash) VALUES (?)", (_hash_admin_key(key),))
    keys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_keys.txt")
    with open(keys_path, "w", encoding="utf-8") as keys_file:
        keys_file.write("\n".join(generated_keys) + "\n")
    print(f"Generated 12 admin keys and saved them to {keys_path}")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        img TEXT NOT NULL,
        price INTEGER NOT NULL,
        decryption TEXT NOT NULL
    )
""")

product_columns = {row[1] for row in cursor.execute("PRAGMA table_info(products)")}
if "user_id" not in product_columns:
    cursor.execute("ALTER TABLE products ADD COLUMN user_id INTEGER REFERENCES users (id) ON DELETE SET NULL")
if "verified" not in product_columns:
    cursor.execute("ALTER TABLE products ADD COLUMN verified INTEGER NOT NULL DEFAULT 0")
    cursor.execute("UPDATE products SET verified = 1")

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

message_columns = {row[1] for row in cursor.execute("PRAGMA table_info(messages)")}
if "edited_at" not in message_columns:
    cursor.execute("ALTER TABLE messages ADD COLUMN edited_at TEXT")

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
            created_at = datetime.now(timezone.utc).isoformat()
            user_data = (name, email, password, created_at)
            cursor.execute(
                "INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
                user_data,
            )
            user_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO admin_notifications (type, reference_id, message, created_at) VALUES (?, ?, ?, ?)",
                ("new_user", user_id, f"New user registered: {name} ({email})", created_at),
            )
        print(f"User added successfully with name: {name}, email: {email}")
        return user_id
    except sqlite3.Error as e:
        print(f"We have caught an error {e}")
        return e

def add_product(name, img, price, decryption, user_id=None):
    try:
        with sql() as con:
            cursor = con.cursor()
            product_data = (name, img, price, decryption, user_id)
            cursor.execute(
                "INSERT INTO products (name, img, price, decryption, user_id, verified) VALUES (?,?,?,?,?,0)",
                product_data,
            )
            product_id = cursor.lastrowid
            uploader = None
            if user_id:
                row = cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
                uploader = row[0] if row else None
            who = f" by {uploader}" if uploader else ""
            cursor.execute(
                "INSERT INTO admin_notifications (type, reference_id, message, created_at) VALUES (?, ?, ?, ?)",
                (
                    "new_product",
                    product_id,
                    f"New product awaiting verification: {name}{who}",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return product_id
    except sqlite3.Error as e:
        print(f"We have caught an error {e}")
        return e

def get_admin_notifications(limit=30):
    with sql() as con:
        return con.execute(
            """SELECT id, type, reference_id, message, created_at
               FROM admin_notifications
               WHERE dismissed = 0
               ORDER BY created_at DESC, id DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

def count_admin_notifications():
    with sql() as con:
        return con.execute(
            "SELECT COUNT(*) FROM admin_notifications WHERE dismissed = 0"
        ).fetchone()[0]

def dismiss_admin_notification(notification_id):
    with sql() as con:
        cursor = con.execute(
            "UPDATE admin_notifications SET dismissed = 1 WHERE id = ?",
            (notification_id,),
        )
        return cursor.rowcount == 1

def dismiss_admin_notifications_for(notification_type, reference_id):
    with sql() as con:
        con.execute(
            "UPDATE admin_notifications SET dismissed = 1 WHERE type = ? AND reference_id = ? AND dismissed = 0",
            (notification_type, reference_id),
        )

def get_verified_products():
    with sql() as con:
        return con.execute(
            """SELECT products.id, products.name, products.img, products.price, products.decryption,
                      users.name, products.user_id
               FROM products
               LEFT JOIN users ON users.id = products.user_id
               WHERE products.verified = 1
               ORDER BY products.id DESC"""
        ).fetchall()

def get_pending_products():
    with sql() as con:
        return con.execute(
            """SELECT products.id, products.name, products.img, products.price, products.decryption,
                      users.name, products.user_id
               FROM products
               LEFT JOIN users ON users.id = products.user_id
               WHERE products.verified = 0
               ORDER BY products.id DESC"""
        ).fetchall()

def get_all_products():
    return get_verified_products()

def set_product_verified(product_id, verified=True):
    with sql() as con:
        cursor = con.execute(
            "UPDATE products SET verified = ? WHERE id = ?",
            (1 if verified else 0, product_id),
        )
        if cursor.rowcount == 1 and verified:
            con.execute(
                "UPDATE admin_notifications SET dismissed = 1 WHERE type = ? AND reference_id = ? AND dismissed = 0",
                ("new_product", product_id),
            )
        return cursor.rowcount == 1

def get_all_users():
    with sql() as con:
        cursor = con.cursor()
        cursor.execute("SELECT id, name, email, role, locked FROM users ORDER BY id")
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
            cursor.execute("SELECT id, locked FROM users WHERE email = ? AND password = ?", (email, password))
            return cursor.fetchone()
    except sqlite3.Error as e:
        return e

def get_user_by_email(email):
    with sql() as con:
        return con.execute("SELECT id, name, email FROM users WHERE email = ?", (email,)).fetchone()

def get_user_by_id_safe(user_id):
    with sql() as con:
        return con.execute(
            "SELECT id, name, email, profile_picture, role, locked, admin_upgrade_key FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

def is_admin(user_id):
    with sql() as con:
        row = con.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        return bool(row and row[0] == "admin")

def is_user_locked(user_id):
    with sql() as con:
        row = con.execute("SELECT locked FROM users WHERE id = ?", (user_id,)).fetchone()
        return bool(row and row[0])

def redeem_admin_key(user_id, key):
    key = (key or "").strip()
    if len(key) != 16:
        return False, "Enter a valid 16-character admin key."
    digest = _hash_admin_key(key)
    with sql() as con:
        user = con.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "User not found."
        if user[0] == "admin":
            return False, "This account is already an admin."
        row = con.execute("SELECT id FROM admin_keys WHERE key_hash = ?", (digest,)).fetchone()
        if not row:
            return False, "That admin key is not valid."
        con.execute(
            "UPDATE users SET role = 'admin', admin_upgrade_key = ? WHERE id = ?",
            (key, user_id),
        )
        return True, None

def _normal_user_target(con, admin_id, target_id):
    admin = con.execute("SELECT role FROM users WHERE id = ?", (admin_id,)).fetchone()
    if not admin or admin[0] != "admin":
        return False, "Admin access is required."
    if int(admin_id) == int(target_id):
        return False, "You cannot manage your own account this way."
    target = con.execute("SELECT role FROM users WHERE id = ?", (target_id,)).fetchone()
    if not target:
        return False, "User not found."
    if target[0] == "admin":
        return False, "Admin accounts cannot be managed this way."
    return True, None

def set_user_locked(admin_id, target_id, locked):
    with sql() as con:
        ok, error = _normal_user_target(con, admin_id, target_id)
        if not ok:
            return False, error
        con.execute("UPDATE users SET locked = ? WHERE id = ?", (1 if locked else 0, target_id))
        return True, None

def delete_user_by_id(admin_id, target_id):
    with sql() as con:
        ok, error = _normal_user_target(con, admin_id, target_id)
        if not ok:
            return False, error
        con.execute("DELETE FROM users WHERE id = ?", (target_id,))
        return True, None

def update_profile_picture(user_id, stored_name):
    with sql() as con:
        con.execute("UPDATE users SET profile_picture = ? WHERE id = ?", (stored_name, user_id))

def get_or_create_storage_folder(user_id, name):
    with sql() as con:
        folder = con.execute(
            "SELECT id FROM storage_folders WHERE user_id = ? AND name = ? AND parent_id IS NULL",
            (user_id, name),
        ).fetchone()
        if folder:
            return folder[0]
        cursor = con.execute(
            "INSERT INTO storage_folders (user_id, name, created_at, parent_id) VALUES (?, ?, ?, NULL)",
            (user_id, name, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid

def ensure_public_share_id(user_id):
    with sql() as con:
        row = con.execute("SELECT public_share_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        if row[0]:
            return row[0]
    for _ in range(8):
        share_id = secrets.token_urlsafe(9)
        try:
            with sql() as con:
                cursor = con.execute(
                    "UPDATE users SET public_share_id = ? WHERE id = ? AND public_share_id IS NULL",
                    (share_id, user_id),
                )
                if cursor.rowcount == 1:
                    return share_id
                existing = con.execute("SELECT public_share_id FROM users WHERE id = ?", (user_id,)).fetchone()
                if existing and existing[0]:
                    return existing[0]
        except sqlite3.IntegrityError:
            continue
    return None

def get_user_by_public_share_id(share_id):
    if not share_id:
        return None
    with sql() as con:
        return con.execute(
            "SELECT id, name, email, profile_picture, public_share_id FROM users WHERE public_share_id = ?",
            (share_id,),
        ).fetchone()

def get_root_public_folder(user_id):
    with sql() as con:
        return con.execute(
            """SELECT id, name, parent_id FROM storage_folders
               WHERE user_id = ? AND parent_id IS NULL AND lower(name) = 'public'
               LIMIT 1""",
            (user_id,),
        ).fetchone()

def is_under_public_folder(user_id, folder_id, public_root_id):
    if folder_id is None or public_root_id is None:
        return False
    if folder_id == public_root_id:
        return True
    with sql() as con:
        row = con.execute(
            """WITH RECURSIVE ancestors(id, parent_id) AS (
                   SELECT id, parent_id FROM storage_folders WHERE id = ? AND user_id = ?
                   UNION ALL
                   SELECT folders.id, folders.parent_id
                   FROM storage_folders folders
                   JOIN ancestors ON folders.id = ancestors.parent_id
                   WHERE folders.user_id = ?
               )
               SELECT 1 FROM ancestors WHERE id = ? LIMIT 1""",
            (folder_id, user_id, user_id, public_root_id),
        ).fetchone()
    return bool(row)

def get_public_folder_path(user_id, folder_id, public_root_id):
    """Return breadcrumb list of (id, name) from public root to folder_id inclusive."""
    if not folder_id or not public_root_id:
        return []
    with sql() as con:
        rows = con.execute(
            """WITH RECURSIVE chain(id, name, parent_id, depth) AS (
                   SELECT id, name, parent_id, 0 FROM storage_folders WHERE id = ? AND user_id = ?
                   UNION ALL
                   SELECT folders.id, folders.name, folders.parent_id, chain.depth + 1
                   FROM storage_folders folders
                   JOIN chain ON folders.id = chain.parent_id
                   WHERE folders.user_id = ?
               )
               SELECT id, name FROM chain ORDER BY depth DESC""",
            (folder_id, user_id, user_id),
        ).fetchall()
    path = []
    seen_public = False
    for row in rows:
        if row[0] == public_root_id:
            seen_public = True
        if seen_public:
            path.append(row)
    return path

def get_public_child_folders(user_id, parent_id):
    with sql() as con:
        return con.execute(
            """SELECT id, name, created_at, parent_id FROM storage_folders
               WHERE user_id = ? AND parent_id = ?
               ORDER BY name COLLATE NOCASE""",
            (user_id, parent_id),
        ).fetchall()

def get_public_folder_files(user_id, folder_id):
    with sql() as con:
        return con.execute(
            """SELECT id, original_name, mime_type, size_bytes, created_at
               FROM storage_items
               WHERE user_id = ? AND folder_id = ?
               ORDER BY original_name COLLATE NOCASE""",
            (user_id, folder_id),
        ).fetchall()

def count_public_shared_files(user_id, public_root_id):
    with sql() as con:
        return con.execute(
            """WITH RECURSIVE tree(id) AS (
                   SELECT id FROM storage_folders WHERE id = ? AND user_id = ?
                   UNION ALL
                   SELECT folders.id FROM storage_folders folders
                   JOIN tree ON folders.parent_id = tree.id
                   WHERE folders.user_id = ?
               )
               SELECT COUNT(*) FROM storage_items
               WHERE user_id = ? AND folder_id IN (SELECT id FROM tree)""",
            (public_root_id, user_id, user_id, user_id),
        ).fetchone()[0]

def get_public_shared_item(share_id, item_id):
    user = get_user_by_public_share_id(share_id)
    if not user:
        return None, None
    public_folder = get_root_public_folder(user[0])
    if not public_folder:
        return user, None
    with sql() as con:
        item = con.execute(
            """SELECT id, user_id, original_name, stored_name, mime_type, size_bytes, folder_id
               FROM storage_items WHERE id = ? AND user_id = ?""",
            (item_id, user[0]),
        ).fetchone()
    if not item or not is_under_public_folder(user[0], item[6], public_folder[0]):
        return user, None
    return user, item

def get_public_share_folder(share_id, folder_id=None):
    """Resolve owner + browsable folder under their public root. folder_id None = public root."""
    user = get_user_by_public_share_id(share_id)
    if not user:
        return None, None, None
    public_root = get_root_public_folder(user[0])
    if not public_root:
        return user, None, None
    if folder_id is None or folder_id == public_root[0]:
        return user, public_root, public_root
    with sql() as con:
        folder = con.execute(
            "SELECT id, name, parent_id FROM storage_folders WHERE id = ? AND user_id = ?",
            (folder_id, user[0]),
        ).fetchone()
    if not folder or not is_under_public_folder(user[0], folder[0], public_root[0]):
        return user, public_root, None
    return user, public_root, folder

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

def delete_storage_folder_tree(folder_id, user_id):
    """Delete a folder, its subfolders, and files. Returns stored file names to remove from disk."""
    with sql() as con:
        folder = con.execute(
            "SELECT id, name FROM storage_folders WHERE id = ? AND user_id = ?",
            (folder_id, user_id),
        ).fetchone()
        if not folder:
            return None
        folder_ids = [
            row[0]
            for row in con.execute(
                """WITH RECURSIVE tree(id) AS (
                       SELECT id FROM storage_folders WHERE id = ? AND user_id = ?
                       UNION ALL
                       SELECT folders.id FROM storage_folders folders
                       JOIN tree ON folders.parent_id = tree.id
                       WHERE folders.user_id = ?
                   ) SELECT id FROM tree""",
                (folder_id, user_id, user_id),
            ).fetchall()
        ]
        placeholders = ",".join("?" * len(folder_ids))
        files = con.execute(
            f"SELECT id, stored_name FROM storage_items WHERE user_id = ? AND folder_id IN ({placeholders})",
            (user_id, *folder_ids),
        ).fetchall()
        stored_names = []
        for file_id, stored_name in files:
            con.execute("DELETE FROM messages WHERE storage_item_id = ? AND body IS NULL", (file_id,))
            con.execute("DELETE FROM storage_items WHERE id = ? AND user_id = ?", (file_id, user_id))
            stored_names.append(stored_name)
        # Delete deepest folders first
        con.execute(
            f"DELETE FROM storage_folders WHERE user_id = ? AND id IN ({placeholders})",
            (user_id, *folder_ids),
        )
        return {"name": folder[1], "stored_names": stored_names}

def unique_item_name(user_id, name, folder_id=None):
    base, ext = os.path.splitext(name)
    candidate = name
    counter = 1
    with sql() as con:
        while True:
            if folder_id is None:
                exists = con.execute(
                    "SELECT 1 FROM storage_items WHERE user_id = ? AND folder_id IS NULL AND original_name = ? COLLATE NOCASE",
                    (user_id, candidate),
                ).fetchone()
            else:
                exists = con.execute(
                    "SELECT 1 FROM storage_items WHERE user_id = ? AND folder_id = ? AND original_name = ? COLLATE NOCASE",
                    (user_id, folder_id, candidate),
                ).fetchone()
            if not exists:
                return candidate
            candidate = f"{base} copy{ext}" if counter == 1 else f"{base} copy {counter}{ext}"
            counter += 1

def unique_folder_name(user_id, name, parent_id=None):
    candidate = name
    counter = 1
    with sql() as con:
        while True:
            exists = con.execute(
                "SELECT 1 FROM storage_folders WHERE user_id = ? AND name = ? COLLATE NOCASE",
                (user_id, candidate),
            ).fetchone()
            if not exists:
                return candidate
            candidate = f"{name} copy" if counter == 1 else f"{name} copy {counter}"
            counter += 1

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
        con.execute("DELETE FROM messages WHERE storage_item_id = ? AND body IS NULL", (item_id,))
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
                      users.name, users.email, messages.body, messages.created_at,
                      users.profile_picture
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

def delete_conversation(conversation_id, user_id):
    with sql() as con:
        cursor = con.execute(
            "DELETE FROM conversations WHERE id = ? AND (user_a_id = ? OR user_b_id = ?)",
            (conversation_id, user_id, user_id),
        )
        return cursor.rowcount == 1

def get_messages(conversation_id, user_id):
    with sql() as con:
        return con.execute(
            """SELECT messages.id, messages.sender_id, users.name, messages.body,
                      messages.storage_item_id, storage_items.original_name,
                      storage_items.mime_type, messages.created_at,
                      users.profile_picture, messages.edited_at
               FROM messages JOIN users ON users.id = messages.sender_id
               LEFT JOIN storage_items ON storage_items.id = messages.storage_item_id
               WHERE messages.conversation_id = ? AND EXISTS (
                   SELECT 1 FROM conversations WHERE id = ? AND (user_a_id = ? OR user_b_id = ?)
               ) ORDER BY messages.created_at""",
            (conversation_id, conversation_id, user_id, user_id),
        ).fetchall()

def search_messages(conversation_id, user_id, query, limit=50):
    query = (query or "").strip()
    if not query:
        return []
    pattern = f"%{query}%"
    with sql() as con:
        return con.execute(
            """SELECT messages.id, messages.sender_id, users.name, messages.body,
                      messages.storage_item_id, storage_items.original_name,
                      storage_items.mime_type, messages.created_at
               FROM messages JOIN users ON users.id = messages.sender_id
               LEFT JOIN storage_items ON storage_items.id = messages.storage_item_id
               WHERE messages.conversation_id = ?
                 AND EXISTS (
                     SELECT 1 FROM conversations WHERE id = ? AND (user_a_id = ? OR user_b_id = ?)
                 )
                 AND (
                     IFNULL(messages.body, '') LIKE ? COLLATE NOCASE
                     OR IFNULL(storage_items.original_name, '') LIKE ? COLLATE NOCASE
                 )
               ORDER BY messages.created_at DESC
               LIMIT ?""",
            (conversation_id, conversation_id, user_id, user_id, pattern, pattern, limit),
        ).fetchall()

def get_conversation_shared_files(conversation_id, user_id):
    with sql() as con:
        if not con.execute(
            "SELECT 1 FROM conversations WHERE id = ? AND (user_a_id = ? OR user_b_id = ?)",
            (conversation_id, user_id, user_id),
        ).fetchone():
            return []
        return con.execute(
            """SELECT storage_items.id, storage_items.original_name, storage_items.stored_name, storage_items.mime_type
               FROM storage_items
               JOIN messages ON messages.storage_item_id = storage_items.id
               WHERE messages.conversation_id = ?
               GROUP BY storage_items.id
               ORDER BY MIN(messages.created_at), storage_items.id""",
            (conversation_id,),
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

def get_message(message_id, user_id):
    with sql() as con:
        return con.execute(
            """SELECT messages.id, messages.conversation_id, messages.sender_id, messages.body,
                      messages.storage_item_id, messages.created_at, messages.edited_at
               FROM messages
               JOIN conversations ON conversations.id = messages.conversation_id
               WHERE messages.id = ?
                 AND (conversations.user_a_id = ? OR conversations.user_b_id = ?)""",
            (message_id, user_id, user_id),
        ).fetchone()

def delete_message(message_id, user_id):
    with sql() as con:
        row = con.execute(
            """SELECT messages.id, messages.conversation_id, messages.storage_item_id,
                      messages.body, storage_items.stored_name, storage_items.mime_type,
                      storage_items.original_name, storage_folders.name
               FROM messages
               JOIN conversations ON conversations.id = messages.conversation_id
               LEFT JOIN storage_items ON storage_items.id = messages.storage_item_id
               LEFT JOIN storage_folders ON storage_folders.id = storage_items.folder_id
               WHERE messages.id = ? AND messages.sender_id = ?
                 AND (conversations.user_a_id = ? OR conversations.user_b_id = ?)""",
            (message_id, user_id, user_id, user_id),
        ).fetchone()
        if not row:
            return None
        message_id_value, conversation_id, storage_item_id, body, stored_name, mime_type, original_name, folder_name = row
        con.execute("DELETE FROM messages WHERE id = ?", (message_id_value,))

        removed_stored_name = None
        if storage_item_id and stored_name:
            name_lower = (original_name or "").lower()
            is_voice = (
                (mime_type or "").lower().startswith("audio/")
                or (folder_name == "Voice_messages")
                or name_lower.startswith("voice-")
                or name_lower.startswith("voice_message")
                or name_lower.startswith("voice.")
            )
            still_used = con.execute(
                "SELECT 1 FROM messages WHERE storage_item_id = ? LIMIT 1",
                (storage_item_id,),
            ).fetchone()
            if is_voice and not still_used:
                con.execute(
                    "DELETE FROM storage_items WHERE id = ? AND user_id = ?",
                    (storage_item_id, user_id),
                )
                removed_stored_name = stored_name

        return {
            "id": message_id_value,
            "conversation_id": conversation_id,
            "stored_name": removed_stored_name,
            "storage_item_id": storage_item_id if removed_stored_name else None,
        }

def update_message_body(message_id, user_id, body):
    body = (body or "").strip()
    if not body:
        return None
    with sql() as con:
        row = con.execute(
            """SELECT messages.id, messages.conversation_id, messages.storage_item_id FROM messages
               JOIN conversations ON conversations.id = messages.conversation_id
               WHERE messages.id = ? AND messages.sender_id = ?
                 AND (conversations.user_a_id = ? OR conversations.user_b_id = ?)""",
            (message_id, user_id, user_id, user_id),
        ).fetchone()
        if not row:
            return None
        edited_at = datetime.now(timezone.utc).isoformat()
        con.execute(
            "UPDATE messages SET body = ?, edited_at = ? WHERE id = ?",
            (body, edited_at, message_id),
        )
        return {
            "id": row[0],
            "conversation_id": row[1],
            "body": body,
            "storage_item_id": row[2],
            "edited_at": edited_at,
        }

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
