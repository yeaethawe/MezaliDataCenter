from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory, abort, jsonify, send_file
from datetime import datetime, timedelta, timezone
import base64
import html
import io
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import shutil
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, join_room
from database import (login_user, get_user_by_id, add_user, get_all_users, update_username,
                      delete_user, get_all_products, get_pending_products, get_verified_products, get_user_by_email, get_user_by_id_safe,
                      add_storage_item, get_storage_items, get_storage_usage, get_storage_item,
                      delete_storage_item, get_or_create_conversation, get_conversation, delete_conversation,
                      get_messages, search_messages, get_conversation_shared_files, add_message, delete_message, update_message_body, can_access_shared_item, search_users,
                      get_user_conversations, get_storage_items_in_folder, get_storage_folders,
                      add_storage_folder, get_storage_folder, rename_storage_item, move_storage_item,
                      update_user_name, change_user_password, update_profile_picture,
                      get_or_create_storage_folder, get_storage_folders_in_folder,
                      move_storage_folder, delete_storage_folder, delete_storage_folder_tree, is_admin, is_user_locked,
                      unique_item_name, unique_folder_name,
                      redeem_admin_key, set_user_locked, delete_user_by_id, set_product_verified,
                      get_admin_notifications, count_admin_notifications, dismiss_admin_notification,
                      dismiss_admin_notifications_for, ensure_public_share_id, get_user_by_public_share_id,
                      get_root_public_folder, get_public_folder_files, get_public_shared_item,
                      get_public_child_folders, get_public_share_folder, get_public_folder_path,
                      count_public_shared_files)
import database
# Get the local computer name
hostname = socket.gethostname()

# Get the local IP address
local_ip = socket.gethostbyname(hostname)

print(f"Hostname: {hostname}")
print(f"Local IP Address: {local_ip}")


# Initialize the Flask application instance
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-this-development-secret"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), "uploads"),
    MAX_CONTENT_LENGTH=500 * 1024 * 1024,
)
socketio = SocketIO(app)
try:
    app.json.ensure_ascii = False
except Exception:
    pass
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
port_number = 80
STORAGE_QUOTA = 1024 * 1024 * 1024
MAX_UPLOAD_SIZE = 500 * 1024 * 1024
EDITABLE_CODE_EXTENSIONS = {
    "py", "pyw", "js", "jsx", "mjs", "cjs", "ts", "tsx", "html", "htm", "css", "scss", "sass", "less",
    "json", "xml", "yaml", "yml", "toml", "ini", "cfg", "conf", "md", "markdown", "txt", "csv", "tsv",
    "sql", "sh", "bash", "zsh", "ps1", "bat", "cmd", "c", "h", "cpp", "hpp", "cc", "cxx", "cs", "java",
    "kt", "kts", "go", "rs", "rb", "php", "swift", "r", "lua", "pl", "pm", "vue", "svelte", "dart",
    "scala", "groovy", "gradle", "properties", "env", "gitignore", "dockerignore", "editorconfig",
    "dockerfile", "makefile", "cmake", "asm", "s", "rake", "gemspec", "ipynb",
}
CODE_MIME_BY_EXTENSION = {
    "py": "text/x-python", "pyw": "text/x-python", "js": "text/javascript", "jsx": "text/javascript",
    "mjs": "text/javascript", "cjs": "text/javascript", "ts": "text/typescript", "tsx": "text/typescript",
    "html": "text/html", "htm": "text/html", "css": "text/css", "scss": "text/x-scss", "sass": "text/x-sass",
    "less": "text/x-less", "json": "application/json", "xml": "application/xml", "yaml": "text/yaml",
    "yml": "text/yaml", "toml": "text/plain", "ini": "text/plain", "cfg": "text/plain", "conf": "text/plain",
    "md": "text/markdown", "markdown": "text/markdown", "txt": "text/plain", "csv": "text/csv",
    "tsv": "text/tab-separated-values", "sql": "application/sql", "sh": "application/x-sh",
    "bash": "application/x-sh", "zsh": "application/x-sh", "ps1": "text/plain", "bat": "text/plain",
    "cmd": "text/plain", "c": "text/x-c", "h": "text/x-c", "cpp": "text/x-c++", "hpp": "text/x-c++",
    "cc": "text/x-c++", "cxx": "text/x-c++", "cs": "text/plain", "java": "text/x-java-source",
    "kt": "text/plain", "kts": "text/plain", "go": "text/x-go", "rs": "text/rust", "rb": "text/x-ruby",
    "php": "application/x-php", "swift": "text/plain", "r": "text/plain", "lua": "text/x-lua",
    "pl": "text/plain", "pm": "text/plain", "vue": "text/plain", "svelte": "text/plain",
    "dart": "text/plain", "scala": "text/plain", "groovy": "text/plain", "gradle": "text/plain",
    "properties": "text/plain", "env": "text/plain", "gitignore": "text/plain",
    "dockerignore": "text/plain", "editorconfig": "text/plain", "dockerfile": "text/plain",
    "makefile": "text/plain", "cmake": "text/plain", "asm": "text/plain", "s": "text/plain",
    "rake": "text/plain", "gemspec": "text/plain", "ipynb": "application/json",
}

def file_extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else ""

def is_editable_file(filename, mime_type=""):
    mime_type = (mime_type or "").lower()
    if mime_type.startswith("text/"):
        return True
    if mime_type in {
        "application/json", "application/javascript", "application/xml", "application/sql",
        "application/x-sh", "application/x-python", "application/x-php", "application/typescript",
    }:
        return True
    return file_extension(filename) in EDITABLE_CODE_EXTENSIONS

def mime_for_filename(filename, fallback="application/octet-stream"):
    return CODE_MIME_BY_EXTENSION.get(file_extension(filename), fallback or "application/octet-stream")

FILETYPE_ICON_BY_EXT = {
    "py": ("bi-filetype-py", "text-warning", "Python"),
    "pyw": ("bi-filetype-py", "text-warning", "Python"),
    "js": ("bi-filetype-js", "text-warning", "JavaScript"),
    "mjs": ("bi-filetype-js", "text-warning", "JavaScript"),
    "cjs": ("bi-filetype-js", "text-warning", "JavaScript"),
    "jsx": ("bi-filetype-jsx", "text-info", "JSX"),
    "ts": ("bi-filetype-tsx", "text-primary", "TypeScript"),
    "tsx": ("bi-filetype-tsx", "text-primary", "TypeScript"),
    "html": ("bi-filetype-html", "text-danger", "HTML"),
    "htm": ("bi-filetype-html", "text-danger", "HTML"),
    "css": ("bi-filetype-css", "text-primary", "CSS"),
    "scss": ("bi-filetype-scss", "text-danger", "SCSS"),
    "sass": ("bi-filetype-sass", "text-danger", "Sass"),
    "json": ("bi-filetype-json", "text-warning", "JSON"),
    "xml": ("bi-filetype-xml", "text-success", "XML"),
    "yml": ("bi-filetype-yml", "text-danger", "YAML"),
    "yaml": ("bi-filetype-yml", "text-danger", "YAML"),
    "md": ("bi-filetype-md", "text-secondary", "Markdown"),
    "markdown": ("bi-filetype-md", "text-secondary", "Markdown"),
    "txt": ("bi-filetype-txt", "text-secondary", "Text"),
    "csv": ("bi-filetype-csv", "text-success", "CSV"),
    "sql": ("bi-filetype-sql", "text-info", "SQL"),
    "sh": ("bi-filetype-sh", "text-success", "Shell"),
    "bash": ("bi-filetype-sh", "text-success", "Shell"),
    "zsh": ("bi-filetype-sh", "text-success", "Shell"),
    "java": ("bi-filetype-java", "text-danger", "Java"),
    "cs": ("bi-filetype-cs", "text-success", "C#"),
    "cpp": ("bi-filetype-cpp", "text-primary", "C++"),
    "cxx": ("bi-filetype-cpp", "text-primary", "C++"),
    "cc": ("bi-filetype-cpp", "text-primary", "C++"),
    "hpp": ("bi-filetype-cpp", "text-primary", "C++"),
    "c": ("bi-file-earmark-code", "text-primary", "C"),
    "h": ("bi-file-earmark-code", "text-primary", "C/C++ header"),
    "php": ("bi-filetype-php", "text-primary", "PHP"),
    "rb": ("bi-filetype-rb", "text-danger", "Ruby"),
    "go": ("bi-file-earmark-code", "text-info", "Go"),
    "rs": ("bi-file-earmark-code", "text-warning", "Rust"),
    "kt": ("bi-file-earmark-code", "text-success", "Kotlin"),
    "swift": ("bi-file-earmark-code", "text-warning", "Swift"),
    "vue": ("bi-file-earmark-code", "text-success", "Vue"),
    "svelte": ("bi-file-earmark-code", "text-danger", "Svelte"),
    "dart": ("bi-file-earmark-code", "text-info", "Dart"),
    "pdf": ("bi-filetype-pdf", "text-danger", "PDF"),
    "doc": ("bi-filetype-doc", "text-primary", "Word"),
    "docx": ("bi-filetype-docx", "text-primary", "Word"),
    "xls": ("bi-filetype-xls", "text-success", "Excel"),
    "xlsx": ("bi-filetype-xlsx", "text-success", "Excel"),
    "ppt": ("bi-filetype-ppt", "text-warning", "PowerPoint"),
    "pptx": ("bi-filetype-pptx", "text-warning", "PowerPoint"),
    "png": ("bi-filetype-png", "text-success", "PNG"),
    "jpg": ("bi-filetype-jpg", "text-success", "JPEG"),
    "jpeg": ("bi-filetype-jpg", "text-success", "JPEG"),
    "gif": ("bi-filetype-gif", "text-success", "GIF"),
    "svg": ("bi-filetype-svg", "text-warning", "SVG"),
    "bmp": ("bi-filetype-bmp", "text-success", "BMP"),
    "webp": ("bi-file-earmark-image", "text-success", "WebP"),
    "ico": ("bi-file-earmark-image", "text-success", "Icon"),
    "mp4": ("bi-filetype-mp4", "text-danger", "Video"),
    "mov": ("bi-filetype-mov", "text-danger", "Video"),
    "webm": ("bi-file-earmark-play", "text-danger", "Video"),
    "mkv": ("bi-file-earmark-play", "text-danger", "Video"),
    "avi": ("bi-file-earmark-play", "text-danger", "Video"),
    "mp3": ("bi-filetype-mp3", "text-info", "Audio"),
    "wav": ("bi-filetype-wav", "text-info", "Audio"),
    "aac": ("bi-filetype-aac", "text-info", "Audio"),
    "flac": ("bi-file-earmark-music", "text-info", "Audio"),
    "ogg": ("bi-file-earmark-music", "text-info", "Audio"),
    "zip": ("bi-file-earmark-zip", "text-warning", "Archive"),
    "rar": ("bi-file-earmark-zip", "text-warning", "Archive"),
    "7z": ("bi-file-earmark-zip", "text-warning", "Archive"),
    "tar": ("bi-file-earmark-zip", "text-warning", "Archive"),
    "gz": ("bi-file-earmark-zip", "text-warning", "Archive"),
    "tgz": ("bi-file-earmark-zip", "text-warning", "Archive"),
    "exe": ("bi-filetype-exe", "text-secondary", "Executable"),
    "dll": ("bi-file-earmark-binary", "text-secondary", "Binary"),
    "bin": ("bi-file-earmark-binary", "text-secondary", "Binary"),
    "ttf": ("bi-filetype-ttf", "text-secondary", "Font"),
    "otf": ("bi-filetype-otf", "text-secondary", "Font"),
    "woff": ("bi-filetype-woff", "text-secondary", "Font"),
    "psd": ("bi-filetype-psd", "text-primary", "Photoshop"),
    "ai": ("bi-filetype-ai", "text-warning", "Illustrator"),
    "env": ("bi-file-earmark-lock", "text-warning", "Environment"),
    "gitignore": ("bi-git", "text-secondary", "Git ignore"),
    "dockerfile": ("bi-box", "text-primary", "Dockerfile"),
    "makefile": ("bi-gear", "text-secondary", "Makefile"),
}

def file_type_icon(filename, mime_type=""):
    ext = file_extension(filename)
    if ext in FILETYPE_ICON_BY_EXT:
        return FILETYPE_ICON_BY_EXT[ext]
    name = (filename or "").lower()
    if name in FILETYPE_ICON_BY_EXT:
        return FILETYPE_ICON_BY_EXT[name]
    if name.startswith("dockerfile"):
        return FILETYPE_ICON_BY_EXT["dockerfile"]
    if name.startswith("makefile"):
        return FILETYPE_ICON_BY_EXT["makefile"]
    mime = (mime_type or "").lower()
    if mime.startswith("image/"):
        return ("bi-file-earmark-image", "text-success", "Image")
    if mime.startswith("video/"):
        return ("bi-file-earmark-play", "text-danger", "Video")
    if mime.startswith("audio/"):
        return ("bi-file-earmark-music", "text-info", "Audio")
    if mime == "application/pdf":
        return ("bi-file-earmark-pdf", "text-danger", "PDF")
    if mime in {"application/zip", "application/x-zip-compressed", "application/x-rar-compressed", "application/x-7z-compressed", "application/gzip", "application/x-tar"}:
        return ("bi-file-earmark-zip", "text-warning", "Archive")
    if "spreadsheet" in mime or "excel" in mime:
        return ("bi-file-earmark-spreadsheet", "text-success", "Spreadsheet")
    if "presentation" in mime or "powerpoint" in mime:
        return ("bi-file-earmark-slides", "text-warning", "Presentation")
    if "word" in mime or "document" in mime:
        return ("bi-file-earmark-word", "text-primary", "Document")
    if mime.startswith("text/") or is_editable_file(filename, mime_type):
        return ("bi-file-earmark-code" if ext in EDITABLE_CODE_EXTENSIONS else "bi-file-earmark-text", "text-primary", "Text")
    return ("bi-file-earmark", "text-secondary", "File")

def current_user_id():
    user_id = session.get("user_id")
    if user_id:
        return int(user_id)
    legacy_user = session.get("user")
    if legacy_user and legacy_user[0]:
        session["user_id"] = legacy_user[0]
        session.pop("user", None)
        return int(legacy_user[0])
    return None

def require_user():
    user_id = current_user_id()
    if not user_id:
        return None, redirect(url_for("login_user_page"))
    user = get_user_by_id_safe(user_id)
    if not user or user[5]:
        session.clear()
        return None, redirect(url_for("login_user_page"))
    return user_id, None

def require_admin():
    user_id, response = require_user()
    if response:
        return None, response
    if not is_admin(user_id):
        return None, (render_template("error.html", error="Admin access is required."), 403)
    return user_id, None

def profile_picture_path(stored_name):
    return os.path.join(app.config["UPLOAD_FOLDER"], stored_name)

@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template("error.html", error="The server does not allow files larger than 500 MB."), 413

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

#print(f"the website is serving on http://{local_ip}:{port_number}")

# Define the route for the home/root URL
@app.route("/", methods=["GET", "POST"])
def main_route():
    return render_template("index.html", is_home=True)

#Define the root for viewing all users
@app.route("/users", methods=["GET", "POST"])
def users_route():
    if request.method == "POST":
        u_name = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        user_id = add_user(u_name, email, password)
        if not isinstance(user_id, int):
            return render_template("error.html", error=user_id), 400
        session["user_id"] = user_id
        session.pop("user", None)
        session.permanent = request.form.get("remember_me") == "on"
        return redirect(url_for("dashboard"))
    return redirect(url_for("register_user_page"))

@app.route('/users/<id>', methods=["GET", "POST"])
def user(id):
    admin_id, response = require_admin()
    if response:
        return response
    return render_template("user.html", users=get_user_by_id(id))

@app.route("/userup", methods=["GET", "POST"])
def userup():
    admin_id, response = require_admin()
    if response:
        return response
    if request.method == "POST":
        u_name = request.form.get("username")
        email = request.form.get("email")
        update_username(u_name, email)
        return render_template("success.html", d1="Username has changed successfully.", d2=u_name)

@app.route("/userdel", methods=["POST"])
def userdel():
    admin_id, response = require_admin()
    if response:
        return response
    email = request.form.get("email")
    target = get_user_by_email(email)
    if not target:
        return render_template("error.html", error="User not found."), 404
    ok, error = delete_user_by_id(admin_id, target[0])
    if not ok:
        return render_template("error.html", error=error), 400
    return render_template("success.html", d1= "The account is deleted with email: ", d2=email)
# Run the app automatically when executing the script

@app.route("/products", methods=["GET","POST"])
def products():
    if request.method == "POST":
        user_id, response = require_user()
        if response:
            return response
        name = (request.form.get("name") or "").strip()
        price = request.form.get("price")
        decryption = (request.form.get("decryption") or "").strip()
        photo = request.files.get("photo")
        if not name or not price or not decryption:
            return render_template("error.html", error="Name, price, and description are required."), 400
        if not photo or not photo.filename:
            return render_template("error.html", error="Please upload a product photo."), 400
        filename = secure_filename(photo.filename)
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in {"jpg", "jpeg", "png", "gif", "webp"}:
            return render_template("error.html", error="Product photos must be JPG, PNG, GIF, or WebP."), 400
        stored_name = f"product_{uuid4().hex}_{filename}"
        photo.save(os.path.join(app.config["UPLOAD_FOLDER"], stored_name))
        result = database.add_product(name, stored_name, price, decryption, user_id)
        if not isinstance(result, int):
            return render_template("error.html", error=result), 400
        return render_template(
            "success.html",
            d1="Product submitted. It will appear after an admin verifies it.",
            d2=f"Product name is {name}",
        )
    viewer_id = current_user_id()
    admin = bool(viewer_id and is_admin(viewer_id))
    return render_template(
        "products.html",
        products=get_verified_products(),
        pending_products=get_pending_products() if admin else [],
        is_admin=admin,
    )

@app.route("/products/add", methods=["GET", "POST"])
def add_product():
    user_id, response = require_user()
    if response:
        return response
    return render_template("addproduct.html")

@app.route("/products/image/<path:stored_name>")
def product_image(stored_name):
    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
    if not stored_name.startswith("product_") or not os.path.isfile(path):
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], stored_name)

@app.route("/admin/products/<int:product_id>/verify", methods=["POST"])
def admin_verify_product(product_id):
    admin_id, response = require_admin()
    if response:
        return response
    if not set_product_verified(product_id, True):
        return render_template("error.html", error="Product not found."), 404
    return redirect(url_for("products"))

@app.route("/admin/products/<int:product_id>/reject", methods=["POST"])
def admin_reject_product(product_id):
    admin_id, response = require_admin()
    if response:
        return response
    product = database.get_product_by_id(product_id)
    if not product:
        return render_template("error.html", error="Product not found."), 404
    row = product[0]
    img = row[2]
    dismiss_admin_notifications_for("new_product", product_id)
    e = database.delete_product(product_id)
    if e:
        return render_template("error.html", error=e), 400
    if img and not str(img).startswith("http"):
        path = os.path.join(app.config["UPLOAD_FOLDER"], img)
        if os.path.isfile(path):
            os.remove(path)
    return redirect(url_for("products"))

@app.route("/products/delete", methods=['POST','GET'])
def del_product():
    if request.method == "POST":
        id = request.form.get("id")
        e = database.delete_product(id)
        if e:
            return render_template("error.html", error=e)
        return render_template("success.html", d1="The product is successfully deleted.", d2=f"product id is {id}")
    return render_template("delproduct.html")

@app.route("/users/delete", methods=['POST', 'GET'])
def del_user():
    admin_id, response = require_admin()
    if response:
        return response
    if request.method == "POST":
        email = request.form.get("email")
        target = get_user_by_email(email)
        if not target:
            return render_template("error.html", error="User not found."), 404
        ok, error = delete_user_by_id(admin_id, target[0])
        if not ok:
            return render_template("error.html", error=error), 400
        return render_template("success.html", d1="The user is successfully deleted.", d2=f"user email is {email}")
    return redirect(url_for("dashboard"))

@app.route("/register")
def register_user_page():
    if current_user_id():
        return redirect(url_for("dashboard"))
    return render_template("register.html", intro_theme=True)

@app.route("/login", methods=["POST", "GET"])
def login_user_page():
    if current_user_id():
        if is_user_locked(current_user_id()) or not get_user_by_id_safe(current_user_id()):
            session.clear()
        else:
            return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        status = login_user(email, password)
        if not status or isinstance(status, Exception):
            return render_template("error.html", error="User not found or incorrect password.")
        if status[1]:
            return render_template("error.html", error="This account is locked.")
        session["user_id"] = status[0]
        session.pop("user", None)
        session.permanent = request.form.get("remember_me") == "on"
        return redirect(url_for("dashboard"))
            
    return render_template("login.html", intro_theme=True)

@app.route("/dashboard")
def dashboard():
    user_id, response = require_user()
    if response:
        return response
    user = get_user_by_id_safe(user_id)
    admin = is_admin(user_id)
    public_folder = get_root_public_folder(user_id)
    public_share_id = ensure_public_share_id(user_id)
    public_files_count = count_public_shared_files(user_id, public_folder[0]) if public_folder else 0
    public_share_url = url_for("public_share", share_id=public_share_id, _external=True) if public_share_id and public_folder else None
    return render_template(
        "dashboard.html",
        user=user,
        is_admin=admin,
        users=get_all_users() if admin else None,
        notifications=get_admin_notifications() if admin else [],
        notification_count=count_admin_notifications() if admin else 0,
        storage_usage=get_storage_usage(user_id),
        storage_quota=STORAGE_QUOTA,
        public_folder=public_folder,
        public_files_count=public_files_count,
        public_share_url=public_share_url,
    )

@app.route("/storage/public-folder", methods=["POST"])
def create_public_folder():
    user_id, response = require_user()
    if response:
        return response
    if get_root_public_folder(user_id):
        return redirect(url_for("dashboard"))
    folder_id = add_storage_folder(user_id, "public", None)
    if not folder_id:
        return render_template("error.html", error="Could not create the public folder. A folder with that name may already exist."), 400
    ensure_public_share_id(user_id)
    return redirect(url_for("file_explorer", folder_id=folder_id))

@app.route("/s/<share_id>")
@app.route("/s/<share_id>/folder/<int:folder_id>")
def public_share(share_id, folder_id=None):
    owner, public_root, current_folder = get_public_share_folder(share_id, folder_id)
    if not owner:
        abort(404)
    if not public_root:
        return render_template(
            "public_share.html",
            owner=owner,
            files=[],
            folders=[],
            share_id=share_id,
            folder_missing=True,
            current_folder=None,
            breadcrumbs=[],
            is_root=True,
        ), 404
    if folder_id is not None and current_folder is None:
        abort(404)
    files = get_public_folder_files(owner[0], current_folder[0])
    folders = get_public_child_folders(owner[0], current_folder[0])
    breadcrumbs = get_public_folder_path(owner[0], current_folder[0], public_root[0])
    return render_template(
        "public_share.html",
        owner=owner,
        files=files,
        folders=folders,
        share_id=share_id,
        folder_missing=False,
        file_type_icon=file_type_icon,
        current_folder=current_folder,
        public_root=public_root,
        breadcrumbs=breadcrumbs,
        is_root=current_folder[0] == public_root[0],
    )

@app.route("/s/<share_id>/file/<int:item_id>")
def public_share_preview(share_id, item_id):
    owner, item = get_public_shared_item(share_id, item_id)
    if not owner or not item:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], item[3], as_attachment=False, mimetype=item[4])

@app.route("/s/<share_id>/file/<int:item_id>/download")
def public_share_download(share_id, item_id):
    owner, item = get_public_shared_item(share_id, item_id)
    if not owner or not item:
        abort(404)
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        item[3],
        as_attachment=True,
        download_name=item[2],
    )

@app.route("/admin/notifications/<int:notification_id>/dismiss", methods=["POST"])
def dismiss_notification(notification_id):
    admin_id, response = require_admin()
    if response:
        return response
    if not dismiss_admin_notification(notification_id):
        abort(404)
    return redirect(url_for("dashboard"))

@app.route("/settings/admin-key", methods=["POST"])
def upgrade_admin_key():
    user_id, response = require_user()
    if response:
        return response
    ok, error = redeem_admin_key(user_id, request.form.get("admin_key", ""))
    if not ok:
        return render_template("error.html", error=error), 400
    return redirect(url_for("dashboard"))

@app.route("/admin/users/<int:target_id>/lock", methods=["POST"])
def admin_lock_user(target_id):
    admin_id, response = require_admin()
    if response:
        return response
    locked = request.form.get("locked") == "1"
    ok, error = set_user_locked(admin_id, target_id, locked)
    if not ok:
        return render_template("error.html", error=error), 400
    return redirect(url_for("dashboard"))

@app.route("/admin/users/<int:target_id>/delete", methods=["POST"])
def admin_delete_user(target_id):
    admin_id, response = require_admin()
    if response:
        return response
    ok, error = delete_user_by_id(admin_id, target_id)
    if not ok:
        return render_template("error.html", error=error), 400
    return redirect(url_for("dashboard"))

@app.route("/settings/profile", methods=["POST"])
def update_profile_settings():
    user_id, response = require_user()
    if response:
        return response
    name = request.form.get("name", "").strip()
    if not name:
        return render_template("error.html", error="Name cannot be empty."), 400
    update_user_name(user_id, name)
    return redirect(url_for("dashboard"))

@app.route("/settings/password", methods=["POST"])
def update_password_settings():
    user_id, response = require_user()
    if response:
        return response
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    if len(new_password) < 6:
        return render_template("error.html", error="New password must contain at least 6 characters."), 400
    if new_password != confirm_password:
        return render_template("error.html", error="New passwords do not match."), 400
    if not change_user_password(user_id, current_password, new_password):
        return render_template("error.html", error="Current password is incorrect."), 400
    return redirect(url_for("dashboard"))

@app.route("/settings/profile-picture", methods=["POST"])
def update_profile_picture_settings():
    user_id, response = require_user()
    if response:
        return response
    image_data = request.form.get("cropped_image", "")
    if not image_data.startswith("data:image/jpeg;base64,"):
        return render_template("error.html", error="Please choose and crop a valid image."), 400
    try:
        image_bytes = base64.b64decode(image_data.split(",", 1)[1], validate=True)
    except (ValueError, base64.binascii.Error):
        return render_template("error.html", error="The cropped image is invalid."), 400
    if len(image_bytes) > 5 * 1024 * 1024:
        return render_template("error.html", error="Profile pictures must be smaller than 5 MB."), 400
    stored_name = f"profile_{user_id}_{uuid4().hex}.jpg"
    with open(profile_picture_path(stored_name), "wb") as image_file:
        image_file.write(image_bytes)
    folder_id = get_or_create_storage_folder(user_id, "Pictures")
    item_id = add_storage_item(user_id, "profile-picture.jpg", stored_name, "image/jpeg", len(image_bytes))
    move_storage_item(item_id, user_id, folder_id)
    update_profile_picture(user_id, stored_name)
    return redirect(url_for("dashboard"))

@app.route("/profile/<int:user_id>")
def view_profile(user_id):
    viewer_id, response = require_user()
    if response:
        return response
    profile = get_user_by_id_safe(user_id)
    if not profile:
        abort(404)
    back = request.args.get("next") or request.referrer or url_for("chat_page")
    if not back.startswith("/") and not back.startswith(request.host_url):
        back = url_for("chat_page")
    return render_template(
        "profile.html",
        profile=profile,
        can_chat=viewer_id != user_id,
        back_url=back,
    )

@app.route("/profile/<int:user_id>/picture")
def profile_picture(user_id):
    viewer_id, response = require_user()
    if response:
        return response
    user = get_user_by_id_safe(user_id)
    if not user or not user[3] or not os.path.isfile(profile_picture_path(user[3])):
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], user[3], mimetype="image/jpeg")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main_route"))

@app.route("/storage/upload", methods=["POST"])
def upload_file():
    user_id, response = require_user()
    if response:
        return response
    file = request.files.get("file")
    if not file or not file.filename:
        return render_template("error.html", error="Please choose a file to upload."), 400
    filename = secure_filename(file.filename)
    if not filename:
        return render_template("error.html", error="Enter a valid file name."), 400
    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)
    if size_bytes > MAX_UPLOAD_SIZE:
        return render_template("error.html", error="The server does not allow files larger than 500 MB."), 413
    if get_storage_usage(user_id) + size_bytes > STORAGE_QUOTA:
        return render_template("error.html", error="This upload exceeds your 1 GB storage quota."), 400
    stored_name = f"{uuid4().hex}_{filename}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], stored_name))
    folder_id = request.form.get("folder_id", type=int)
    if folder_id is not None and not get_storage_folder(folder_id, user_id):
        folder_id = None
    mime_type = CODE_MIME_BY_EXTENSION.get(file_extension(filename)) or file.mimetype or "application/octet-stream"
    item_id = add_storage_item(user_id, filename, stored_name, mime_type, size_bytes)
    if folder_id is not None:
        move_storage_item(item_id, user_id, folder_id)
    return redirect(request.form.get("next") or url_for("dashboard"))

@app.route("/storage/<int:item_id>/download")
def download_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    item = get_storage_item(item_id)
    if not item or item[1] != user_id:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], item[3], as_attachment=True, download_name=item[2])

@app.route("/storage/<int:item_id>/delete", methods=["POST"])
def remove_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    stored_name = delete_storage_item(item_id, user_id)
    if not stored_name:
        abort(404)
    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
    if os.path.exists(path):
        os.remove(path)
    return redirect(request.form.get("next") or url_for("dashboard"))

@app.route("/files")
def file_explorer():
    user_id, response = require_user()
    if response:
        return response
    folder_id = request.args.get("folder_id", type=int)
    if folder_id is not None and not get_storage_folder(folder_id, user_id):
        abort(404)
    return render_template(
        "files.html",
        folders=get_storage_folders(user_id),
        child_folders=get_storage_folders_in_folder(user_id, folder_id),
        current_folder=get_storage_folder(folder_id, user_id) if folder_id else None,
        parent_folder=get_storage_folder(get_storage_folder(folder_id, user_id)[2], user_id) if folder_id and get_storage_folder(folder_id, user_id)[2] else None,
        files=get_storage_items_in_folder(user_id, folder_id),
        all_files=get_storage_items(user_id),
        storage_usage=get_storage_usage(user_id),
        storage_quota=STORAGE_QUOTA,
        is_editable_file=is_editable_file,
        file_extension=file_extension,
        editable_code_extensions=EDITABLE_CODE_EXTENSIONS,
        file_type_icon=file_type_icon,
    )

@app.route("/files/folders", methods=["POST"])
def create_folder():
    user_id, response = require_user()
    if response:
        return response
    name = secure_filename(request.form.get("name", "").strip())
    if not name:
        return render_template("error.html", error="Enter a valid folder name."), 400
    parent_id = request.form.get("folder_id", type=int)
    if parent_id is not None and not get_storage_folder(parent_id, user_id):
        abort(404)
    if not add_storage_folder(user_id, name, parent_id):
        return render_template("error.html", error="A folder with that name already exists."), 400
    return redirect(url_for("file_explorer", folder_id=parent_id))

@app.route("/files/create", methods=["POST"])
def create_file():
    user_id, response = require_user()
    if response:
        return response
    name = secure_filename(request.form.get("name", "").strip())
    folder_id = request.form.get("folder_id", type=int)
    if folder_id is not None and not get_storage_folder(folder_id, user_id):
        abort(404)
    if not name:
        return render_template("error.html", error="Enter a valid file name."), 400
    stored_name = f"{uuid4().hex}_{name}"
    open(os.path.join(app.config["UPLOAD_FOLDER"], stored_name), "wb").close()
    mime_type = mime_for_filename(name, "text/plain")
    item_id = add_storage_item(user_id, name, stored_name, mime_type, 0)
    if folder_id is not None:
        move_storage_item(item_id, user_id, folder_id)
    return redirect(url_for("file_explorer", folder_id=folder_id))

@app.route("/files/<int:item_id>/rename", methods=["POST"])
def rename_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    name = secure_filename(request.form.get("name", "").strip())
    old_item = get_storage_item(item_id)
    if not old_item or old_item[1] != user_id or not name or "." not in name:
        return render_template("error.html", error="Enter a valid file name."), 400
    old_extension = old_item[2].rsplit(".", 1)[-1].lower()
    if name.rsplit(".", 1)[-1].lower() != old_extension:
        return render_template("error.html", error="Keep the original file extension."), 400
    rename_storage_item(item_id, user_id, name)
    return redirect(url_for("file_explorer", folder_id=request.form.get("folder_id", type=int)))

@app.route("/files/<int:item_id>/move", methods=["POST"])
def move_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    folder_id = request.form.get("folder_id", type=int)
    if not move_storage_item(item_id, user_id, folder_id):
        abort(404)
    return redirect(url_for("file_explorer", folder_id=request.form.get("current_folder_id", type=int)))

@app.route("/files/folders/<int:folder_id>/move", methods=["POST"])
def move_folder(folder_id):
    user_id, response = require_user()
    if response:
        return response
    parent_id = request.form.get("parent_id", type=int)
    if not move_storage_folder(folder_id, user_id, parent_id):
        abort(400)
    return redirect(url_for("file_explorer", folder_id=request.form.get("current_folder_id", type=int)))

@app.route("/files/folders/<int:folder_id>/delete", methods=["POST"])
def delete_folder(folder_id):
    user_id, response = require_user()
    if response:
        return response
    if not delete_storage_folder(folder_id, user_id):
        abort(404)
    return redirect(url_for("file_explorer", folder_id=request.form.get("current_folder_id", type=int)))

@app.route("/files/<int:item_id>/preview")
def preview_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    item = get_storage_item(item_id)
    if not item or item[1] != user_id:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], item[3], as_attachment=False, mimetype=item[4])

@app.route("/files/<int:item_id>/edit", methods=["POST"])
def edit_text_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    item = get_storage_item(item_id)
    if not item or item[1] != user_id or not is_editable_file(item[2], item[4]):
        abort(404)
    content = request.form.get("content", "")
    path = os.path.join(app.config["UPLOAD_FOLDER"], item[3])
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(content)
    size_bytes = os.path.getsize(path)
    with database.sql() as con:
        con.execute(
            "UPDATE storage_items SET size_bytes = ? WHERE id = ? AND user_id = ?",
            (size_bytes, item_id, user_id),
        )
    return redirect(url_for("file_explorer", folder_id=request.form.get("folder_id", type=int)))

MAX_IDE_FILE_BYTES = 5 * 1024 * 1024

def _owned_item(item_id, user_id):
    item = get_storage_item(item_id)
    if not item or item[1] != user_id:
        return None
    return item

def _owned_editable_item(item_id, user_id):
    item = _owned_item(item_id, user_id)
    if not item or not is_editable_file(item[2], item[4]):
        return None
    return item

def ide_file_mode(filename, mime_type=""):
    mime = (mime_type or "").lower()
    if is_editable_file(filename, mime_type):
        return "edit"
    ext = file_extension(filename)
    if mime.startswith("image/") or ext in {"png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico"}:
        return "image"
    if mime.startswith("video/") or ext in {"mp4", "webm", "mov", "mkv", "avi", "ogg"}:
        return "video"
    if mime.startswith("audio/") or ext in {"mp3", "wav", "aac", "flac", "m4a", "oga"}:
        return "audio"
    if mime == "application/pdf" or ext == "pdf":
        return "pdf"
    return "none"

def _build_ide_tree(user_id):
    folders = get_storage_folders(user_id)
    with database.sql() as con:
        files = con.execute(
            "SELECT id, original_name, mime_type, size_bytes, folder_id FROM storage_items WHERE user_id = ? ORDER BY original_name COLLATE NOCASE",
            (user_id,),
        ).fetchall()
    folder_nodes = {
        folder[0]: {
            "id": folder[0],
            "name": folder[1],
            "parent_id": folder[3],
            "type": "folder",
            "children": [],
        }
        for folder in folders
    }
    roots = []
    for folder in folders:
        node = folder_nodes[folder[0]]
        parent_id = folder[3]
        if parent_id and parent_id in folder_nodes:
            folder_nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)
    for file in files:
        icon, color, _label = file_type_icon(file[1], file[2])
        mode = ide_file_mode(file[1], file[2])
        file_node = {
            "id": file[0],
            "name": file[1],
            "mime": file[2],
            "size": file[3],
            "type": "file",
            "icon": icon,
            "color": color,
            "editable": mode == "edit",
            "mode": mode,
        }
        folder_id = file[4]
        if folder_id and folder_id in folder_nodes:
            folder_nodes[folder_id]["children"].append(file_node)
        else:
            roots.append(file_node)

    def sort_children(nodes):
        nodes.sort(key=lambda n: (0 if n["type"] == "folder" else 1, n["name"].lower()))
        for node in nodes:
            if node.get("children"):
                sort_children(node["children"])

    sort_children(roots)
    return roots

@app.route("/ide")
@app.route("/ide/<int:item_id>")
def ide_page(item_id=None):
    user_id, response = require_user()
    if response:
        return response
    open_file = None
    if item_id is not None:
        item = _owned_item(item_id, user_id)
        if not item:
            abort(404)
        mode = ide_file_mode(item[2], item[4])
        open_file = {
            "id": item[0],
            "name": item[2],
            "mime": item[4],
            "editable": mode == "edit",
            "mode": mode,
        }
    return render_template("ide.html", open_file=open_file)

@app.route("/api/ide/tree")
def ide_tree():
    user_id, response = require_user()
    if response:
        return response
    return jsonify({"tree": _build_ide_tree(user_id)})

@app.route("/api/ide/files/<int:item_id>", methods=["GET", "PUT"])
def ide_file_api(item_id):
    user_id, response = require_user()
    if response:
        return response
    item = _owned_item(item_id, user_id)
    if not item:
        abort(404)
    path = os.path.join(app.config["UPLOAD_FOLDER"], item[3])
    if not os.path.exists(path):
        abort(404)
    mode = ide_file_mode(item[2], item[4])
    if request.method == "GET":
        payload = {
            "id": item[0],
            "name": item[2],
            "mime": item[4],
            "size": os.path.getsize(path),
            "mode": mode,
            "editable": mode == "edit",
            "preview_url": url_for("preview_file", item_id=item_id),
            "download_url": url_for("download_file", item_id=item_id),
        }
        if mode == "edit":
            if os.path.getsize(path) > MAX_IDE_FILE_BYTES:
                return jsonify({"error": "File is larger than 5 MB and cannot be opened in the IDE editor."}), 413
            with open(path, "r", encoding="utf-8", errors="replace") as file:
                payload["content"] = file.read()
        return jsonify(payload)
    if mode != "edit":
        return jsonify({"error": "This file type cannot be edited in the IDE."}), 400
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    if content is None:
        return jsonify({"error": "Missing content."}), 400
    if not isinstance(content, str):
        return jsonify({"error": "Content must be a string."}), 400
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_IDE_FILE_BYTES:
        return jsonify({"error": "Saved content exceeds the 5 MB IDE limit."}), 413
    usage = get_storage_usage(user_id) - item[5] + len(encoded)
    if usage > STORAGE_QUOTA:
        return jsonify({"error": "Saving would exceed your 1 GB storage quota."}), 400
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(content)
    size_bytes = os.path.getsize(path)
    with database.sql() as con:
        con.execute(
            "UPDATE storage_items SET size_bytes = ? WHERE id = ? AND user_id = ?",
            (size_bytes, item_id, user_id),
        )
    return jsonify({"ok": True, "id": item_id, "size": size_bytes})

@app.route("/api/ide/files", methods=["POST"])
def ide_create_file():
    user_id, response = require_user()
    if response:
        return response
    payload = request.get_json(silent=True) or {}
    name = secure_filename((payload.get("name") or "").strip())
    folder_id = payload.get("folder_id")
    if folder_id in ("", None):
        folder_id = None
    else:
        try:
            folder_id = int(folder_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid folder."}), 400
        if not get_storage_folder(folder_id, user_id):
            return jsonify({"error": "Folder not found."}), 404
    if not name:
        return jsonify({"error": "Enter a valid file name."}), 400
    if not is_editable_file(name):
        return jsonify({"error": "Choose a code or text file extension (for example .py or .js)."}), 400
    stored_name = f"{uuid4().hex}_{name}"
    open(os.path.join(app.config["UPLOAD_FOLDER"], stored_name), "wb").close()
    mime_type = mime_for_filename(name, "text/plain")
    item_id = add_storage_item(user_id, name, stored_name, mime_type, 0)
    if folder_id is not None:
        move_storage_item(item_id, user_id, folder_id)
    icon, color, label = file_type_icon(name, mime_type)
    return jsonify({
        "ok": True,
        "id": item_id,
        "name": name,
        "mime": mime_type,
        "folder_id": folder_id,
        "icon": icon,
        "color": color,
        "label": label,
    }), 201

@app.route("/api/ide/folders", methods=["POST"])
def ide_create_folder():
    user_id, response = require_user()
    if response:
        return response
    payload = request.get_json(silent=True) or {}
    name = secure_filename((payload.get("name") or "").strip())
    parent_id = payload.get("folder_id")
    if parent_id in ("", None):
        parent_id = None
    else:
        try:
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid folder."}), 400
        if not get_storage_folder(parent_id, user_id):
            return jsonify({"error": "Parent folder not found."}), 404
    if not name:
        return jsonify({"error": "Enter a valid folder name."}), 400
    folder_id = add_storage_folder(user_id, name, parent_id)
    if not folder_id:
        return jsonify({"error": "A folder with that name already exists."}), 400
    return jsonify({"ok": True, "id": folder_id, "name": name, "parent_id": parent_id}), 201

def _parse_optional_folder_id(payload, user_id):
    folder_id = payload.get("folder_id")
    if folder_id in ("", None):
        return None, None
    try:
        folder_id = int(folder_id)
    except (TypeError, ValueError):
        return None, (jsonify({"error": "Invalid folder."}), 400)
    if not get_storage_folder(folder_id, user_id):
        return None, (jsonify({"error": "Folder not found."}), 404)
    return folder_id, None

@app.route("/api/ide/files/<int:item_id>/move", methods=["POST"])
def ide_move_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    item = get_storage_item(item_id)
    if not item or item[1] != user_id:
        abort(404)
    payload = request.get_json(silent=True) or {}
    folder_id, error = _parse_optional_folder_id(payload, user_id)
    if error:
        return error
    if not move_storage_item(item_id, user_id, folder_id):
        return jsonify({"error": "Could not move file."}), 400
    return jsonify({"ok": True, "id": item_id, "folder_id": folder_id})

@app.route("/api/ide/folders/<int:folder_id>/move", methods=["POST"])
def ide_move_folder(folder_id):
    user_id, response = require_user()
    if response:
        return response
    if not get_storage_folder(folder_id, user_id):
        abort(404)
    payload = request.get_json(silent=True) or {}
    parent_id, error = _parse_optional_folder_id(payload, user_id)
    if error:
        return error
    if parent_id == folder_id:
        return jsonify({"error": "Cannot move a folder into itself."}), 400
    if not move_storage_folder(folder_id, user_id, parent_id):
        return jsonify({"error": "Could not move folder. Check that the destination is valid."}), 400
    return jsonify({"ok": True, "id": folder_id, "parent_id": parent_id})

def _storage_path_for(user_id, folder_id):
    parts = []
    current = folder_id
    seen = set()
    while current is not None and current not in seen:
        seen.add(current)
        folder = get_storage_folder(current, user_id)
        if not folder:
            break
        parts.append(folder[1])
        current = folder[2]
    parts.reverse()
    return "/" + "/".join(parts) if parts else "/Root"

@app.route("/api/ide/files/<int:item_id>/detail")
def ide_file_detail(item_id):
    user_id, response = require_user()
    if response:
        return response
    item = get_storage_item(item_id)
    if not item or item[1] != user_id:
        abort(404)
    folder_id = item[7] if len(item) > 7 else None
    return jsonify({
        "type": "file",
        "id": item[0],
        "name": item[2],
        "mime": item[4],
        "size": item[5],
        "created_at": item[6],
        "folder_id": folder_id,
        "path": f"{_storage_path_for(user_id, folder_id)}/{item[2]}",
        "mode": ide_file_mode(item[2], item[4]),
    })

@app.route("/api/ide/folders/<int:folder_id>/detail")
def ide_folder_detail(folder_id):
    user_id, response = require_user()
    if response:
        return response
    folder = get_storage_folder(folder_id, user_id)
    if not folder:
        abort(404)
    with database.sql() as con:
        file_count = con.execute(
            "SELECT COUNT(*) FROM storage_items WHERE user_id = ? AND folder_id = ?",
            (user_id, folder_id),
        ).fetchone()[0]
        child_count = con.execute(
            "SELECT COUNT(*) FROM storage_folders WHERE user_id = ? AND parent_id = ?",
            (user_id, folder_id),
        ).fetchone()[0]
        created = con.execute(
            "SELECT created_at FROM storage_folders WHERE id = ? AND user_id = ?",
            (folder_id, user_id),
        ).fetchone()
    return jsonify({
        "type": "folder",
        "id": folder[0],
        "name": folder[1],
        "parent_id": folder[2],
        "created_at": created[0] if created else None,
        "path": _storage_path_for(user_id, folder_id),
        "files": file_count,
        "folders": child_count,
    })

@app.route("/api/ide/files/<int:item_id>", methods=["DELETE"])
def ide_delete_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    stored_name = delete_storage_item(item_id, user_id)
    if not stored_name:
        abort(404)
    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
    if os.path.isfile(path):
        os.remove(path)
    return jsonify({"ok": True, "id": item_id})

@app.route("/api/ide/folders/<int:folder_id>", methods=["DELETE"])
def ide_delete_folder(folder_id):
    user_id, response = require_user()
    if response:
        return response
    result = delete_storage_folder_tree(folder_id, user_id)
    if not result:
        abort(404)
    for stored_name in result["stored_names"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        if os.path.isfile(path):
            os.remove(path)
    return jsonify({"ok": True, "id": folder_id, "name": result["name"]})

@app.route("/api/ide/files/<int:item_id>/copy", methods=["POST"])
def ide_copy_file(item_id):
    user_id, response = require_user()
    if response:
        return response
    item = get_storage_item(item_id)
    if not item or item[1] != user_id:
        abort(404)
    payload = request.get_json(silent=True) or {}
    folder_id, error = _parse_optional_folder_id(payload, user_id)
    if error:
        return error
    src_path = os.path.join(app.config["UPLOAD_FOLDER"], item[3])
    if not os.path.isfile(src_path):
        return jsonify({"error": "Source file is missing on disk."}), 404
    size_bytes = item[5]
    if get_storage_usage(user_id) + size_bytes > STORAGE_QUOTA:
        return jsonify({"error": "Copy would exceed your storage quota."}), 400
    new_name = unique_item_name(user_id, item[2], folder_id)
    stored_name = f"{uuid4().hex}_{secure_filename(new_name) or 'copy'}"
    shutil.copy2(src_path, os.path.join(app.config["UPLOAD_FOLDER"], stored_name))
    new_id = add_storage_item(user_id, new_name, stored_name, item[4], size_bytes)
    if folder_id is not None:
        move_storage_item(new_id, user_id, folder_id)
    return jsonify({"ok": True, "id": new_id, "name": new_name, "folder_id": folder_id})

@app.route("/api/ide/folders/<int:folder_id>/copy", methods=["POST"])
def ide_copy_folder(folder_id):
    user_id, response = require_user()
    if response:
        return response
    source = get_storage_folder(folder_id, user_id)
    if not source:
        abort(404)
    payload = request.get_json(silent=True) or {}
    parent_id, error = _parse_optional_folder_id(payload, user_id)
    if error:
        return error
    if parent_id == folder_id:
        return jsonify({"error": "Cannot paste a folder into itself."}), 400

    def copy_tree(src_folder_id, dest_parent_id):
        src = get_storage_folder(src_folder_id, user_id)
        if not src:
            return None
        new_folder_name = unique_folder_name(user_id, src[1], dest_parent_id)
        new_folder_id = add_storage_folder(user_id, new_folder_name, dest_parent_id)
        if not new_folder_id:
            new_folder_name = unique_folder_name(user_id, f"{src[1]} copy", dest_parent_id)
            new_folder_id = add_storage_folder(user_id, new_folder_name, dest_parent_id)
        if not new_folder_id:
            return None
        for child in get_storage_folders_in_folder(user_id, src_folder_id):
            copy_tree(child[0], new_folder_id)
        for file in get_storage_items_in_folder(user_id, src_folder_id):
            item = get_storage_item(file[0])
            if not item:
                continue
            src_path = os.path.join(app.config["UPLOAD_FOLDER"], item[3])
            if not os.path.isfile(src_path):
                continue
            if get_storage_usage(user_id) + item[5] > STORAGE_QUOTA:
                continue
            new_name = unique_item_name(user_id, item[2], new_folder_id)
            stored_name = f"{uuid4().hex}_{secure_filename(new_name) or 'copy'}"
            shutil.copy2(src_path, os.path.join(app.config["UPLOAD_FOLDER"], stored_name))
            new_id = add_storage_item(user_id, new_name, stored_name, item[4], item[5])
            move_storage_item(new_id, user_id, new_folder_id)
        return new_folder_id

    new_id = copy_tree(folder_id, parent_id)
    if not new_id:
        return jsonify({"error": "Could not copy folder."}), 400
    return jsonify({"ok": True, "id": new_id, "parent_id": parent_id})

@app.route("/chat")
def chat_page():
    user_id, response = require_user()
    if response:
        return response
    search_query = request.args.get("q", "").strip()
    search_results = search_users(search_query, user_id) if search_query else []
    conversation_id = request.args.get("conversation_id", type=int)
    selected_user_id = request.args.get("user_id", type=int)
    other_email = request.args.get("email")
    if not selected_user_id and other_email:
        other_user_by_email = get_user_by_email(other_email)
        selected_user_id = other_user_by_email[0] if other_user_by_email else None
    if selected_user_id:
        conversation = get_or_create_conversation(user_id, selected_user_id)
    elif conversation_id:
        conversation = get_conversation(conversation_id, user_id)
    else:
        conversation = None
    other_user = None
    if conversation:
        other_user_id = conversation[2] if conversation[1] == user_id else conversation[1]
        other_user = get_user_by_id_safe(other_user_id)
    messages = get_messages(conversation[0], user_id) if conversation else []
    return render_template(
        "chat.html",
        user=get_user_by_id_safe(user_id),
        other_user=other_user,
        conversation=conversation,
        conversations=get_user_conversations(user_id),
        search_query=search_query,
        search_results=search_results,
        messages=messages,
        storage_items=get_storage_items(user_id),
        storage_browser_index=_storage_browser_index(user_id),
        file_type_icon=file_type_icon,
    )

def _storage_browser_payload(user_id, folder_id=None):
    if folder_id is not None and not get_storage_folder(folder_id, user_id):
        return None
    current = get_storage_folder(folder_id, user_id) if folder_id else None
    folders = get_storage_folders_in_folder(user_id, folder_id)
    files = get_storage_items_in_folder(user_id, folder_id)
    return {
        "folder_id": folder_id,
        "folder_name": current[1] if current else "Root",
        "parent_id": current[2] if current else None,
        "folders": [{"id": folder[0], "name": folder[1], "parent_id": folder[3]} for folder in folders],
        "files": [
            {
                "id": item[0],
                "name": item[1],
                "mime": item[2],
                "size": item[3],
                "folder_id": item[5],
                "icon": file_type_icon(item[1], item[2])[0],
                "color": file_type_icon(item[1], item[2])[1],
                "preview_url": url_for("preview_file", item_id=item[0]) if (item[2] or "").startswith(("image/", "video/")) else None,
            }
            for item in files
        ],
    }

def _storage_browser_index(user_id):
    folders = [
        {"id": folder[0], "name": folder[1], "parent_id": folder[3]}
        for folder in get_storage_folders(user_id)
    ]
    with database.sql() as con:
        rows = con.execute(
            "SELECT id, original_name, mime_type, size_bytes, folder_id FROM storage_items WHERE user_id = ? ORDER BY original_name COLLATE NOCASE",
            (user_id,),
        ).fetchall()
    files = [
        {
            "id": item[0],
            "name": item[1],
            "mime": item[2],
            "size": item[3],
            "folder_id": item[4],
            "icon": file_type_icon(item[1], item[2])[0],
            "color": file_type_icon(item[1], item[2])[1],
            "preview_url": url_for("preview_file", item_id=item[0]) if (item[2] or "").startswith(("image/", "video/")) else None,
        }
        for item in rows
    ]
    return {"folders": folders, "files": files}

@app.route("/api/storage/browse")
def storage_browse():
    user_id, response = require_user()
    if response:
        if request.accept_mimetypes.best == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.path.startswith("/api/"):
            return jsonify({"error": "authentication_required", "folders": [], "files": []}), 401
        return response
    folder_id = request.args.get("folder_id", type=int)
    payload = _storage_browser_payload(user_id, folder_id)
    if payload is None:
        return jsonify({"error": "folder_not_found", "folders": [], "files": []}), 404
    return jsonify(payload)

@app.route("/chat/<int:conversation_id>/delete", methods=["POST"])
def delete_chat(conversation_id):
    user_id, response = require_user()
    if response:
        return response
    if not delete_conversation(conversation_id, user_id):
        abort(404)
    return redirect(url_for("chat_page"))

@app.route("/chat/<int:conversation_id>/export")
def export_chat(conversation_id):
    user_id, response = require_user()
    if response:
        return response
    conversation = get_conversation(conversation_id, user_id)
    if not conversation:
        abort(404)
    other_user_id = conversation[2] if conversation[1] == user_id else conversation[1]
    other_user = get_user_by_id_safe(other_user_id)
    me = get_user_by_id_safe(user_id)
    messages = get_messages(conversation_id, user_id)
    shared_files = get_conversation_shared_files(conversation_id, user_id)

    used_names = set()
    file_paths = {}
    for item_id, original_name, stored_name, mime_type in shared_files:
        safe_name = secure_filename(original_name) or f"file-{item_id}"
        base, ext = os.path.splitext(safe_name)
        candidate = safe_name
        counter = 1
        while candidate.lower() in used_names:
            candidate = f"{base}-{counter}{ext}"
            counter += 1
        used_names.add(candidate.lower())
        file_paths[item_id] = (candidate, stored_name, mime_type or "")

    peer_label = other_user[1] if other_user else "chat"
    message_blocks = []
    for message in messages:
        sender = html.escape(message[2] or "Unknown")
        created = html.escape((message[7] or "")[:19].replace("T", " "))
        parts = [f'<article class="message"><header><strong>{sender}</strong> <time>{created}</time></header>']
        if message[3]:
            parts.append(f"<p>{html.escape(message[3])}</p>")
        if message[4] and message[4] in file_paths:
            zip_name, _, mime_type = file_paths[message[4]]
            href = html.escape(f"files/{zip_name}")
            label = html.escape(message[5] or zip_name)
            if mime_type.startswith("image/"):
                parts.append(f'<p><a href="{href}"><img src="{href}" alt="{label}"></a></p>')
            else:
                parts.append(f'<p>Attachment: <a href="{href}">{label}</a></p>')
        parts.append("</article>")
        message_blocks.append("\n".join(parts))

    chat_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat with {html.escape(peer_label)}</title>
<style>
body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 44rem; color: #1a1a1a; line-height: 1.5; }}
h1 {{ font-size: 1.5rem; }}
.meta {{ color: #555; margin-bottom: 1.5rem; }}
.message {{ border-top: 1px solid #ddd; padding: 0.9rem 0; }}
.message header {{ color: #555; font-size: 0.9rem; margin-bottom: 0.35rem; }}
.message img {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<h1>Chat with {html.escape(peer_label)}</h1>
<p class="meta">Exported for {html.escape(me[1] if me else "user")} · {len(messages)} messages · {len(file_paths)} files</p>
{"".join(message_blocks) if message_blocks else "<p>No messages in this conversation.</p>"}
</body>
</html>
"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("chat.html", chat_html.encode("utf-8"))
        for item_id, (zip_name, stored_name, _) in file_paths.items():
            path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
            if os.path.isfile(path):
                archive.write(path, arcname=f"files/{zip_name}")
    buffer.seek(0)
    download_name = secure_filename(f"chat-with-{peer_label}.zip") or f"chat-{conversation_id}.zip"
    return send_file(buffer, as_attachment=True, download_name=download_name, mimetype="application/zip")

@app.route("/chat/history/<int:conversation_id>")
def chat_history(conversation_id):
    user_id, response = require_user()
    if response:
        return response
    if not get_conversation(conversation_id, user_id):
        abort(404)
    return jsonify([{"id": row[0], "sender_id": row[1], "sender_name": row[2], "body": row[3], "storage_item_id": row[4], "filename": row[5], "mime_type": row[6], "created_at": row[7], "profile_picture": row[8], "edited_at": row[9] if len(row) > 9 else None} for row in get_messages(conversation_id, user_id)])

@app.route("/chat/<int:conversation_id>/messages/<int:message_id>", methods=["DELETE"])
def chat_delete_message(conversation_id, message_id):
    user_id, response = require_user()
    if response:
        return response
    if not get_conversation(conversation_id, user_id):
        abort(404)
    deleted = delete_message(message_id, user_id)
    if not deleted or deleted["conversation_id"] != conversation_id:
        return jsonify({"error": "Message not found or not allowed."}), 404
    stored_name = deleted.get("stored_name")
    if stored_name:
        path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        if os.path.isfile(path):
            os.remove(path)
    socketio.emit(
        "message_deleted",
        {"id": message_id, "conversation_id": conversation_id},
        room=f"conversation:{conversation_id}",
    )
    return jsonify({"ok": True, "id": message_id})

@app.route("/chat/<int:conversation_id>/messages/<int:message_id>", methods=["PATCH"])
def chat_edit_message(conversation_id, message_id):
    user_id, response = require_user()
    if response:
        return response
    if not get_conversation(conversation_id, user_id):
        abort(404)
    payload = request.get_json(silent=True) or {}
    body = sanitize_chat_body((payload.get("body") or "").strip() or None)
    if not body:
        return jsonify({"error": "Message text is required."}), 400
    updated = update_message_body(message_id, user_id, body)
    if not updated or updated["conversation_id"] != conversation_id:
        return jsonify({"error": "Message not found or not allowed."}), 404
    socketio.emit(
        "message_updated",
        {
            "id": message_id,
            "conversation_id": conversation_id,
            "body": updated["body"],
            "edited_at": updated["edited_at"],
            "storage_item_id": updated["storage_item_id"],
        },
        room=f"conversation:{conversation_id}",
    )
    return jsonify({"ok": True, "message": updated})

@app.route("/chat/<int:conversation_id>/search")
def chat_search(conversation_id):
    user_id, response = require_user()
    if response:
        return response
    if not get_conversation(conversation_id, user_id):
        abort(404)
    query = request.args.get("q", "").strip()
    rows = search_messages(conversation_id, user_id, query)
    return jsonify([
        {
            "id": row[0],
            "sender_id": row[1],
            "sender_name": row[2],
            "body": row[3],
            "storage_item_id": row[4],
            "filename": row[5],
            "mime_type": row[6],
            "created_at": row[7],
        }
        for row in rows
    ])

CURATED_GIFS = [
    {"id": "thumbsup", "title": "Thumbs up", "url": "https://media.giphy.com/media/111ebonMs90YLu/giphy.gif", "tags": "yes ok thumbs"},
    {"id": "clap", "title": "Clap", "url": "https://media.giphy.com/media/7rj2Zg2X0SftXCSnY7/giphy.gif", "tags": "clap applause"},
    {"id": "lol", "title": "LOL", "url": "https://media.giphy.com/media/10JhviFuU2gWD6/giphy.gif", "tags": "lol laugh funny"},
    {"id": "love", "title": "Love", "url": "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif", "tags": "love heart"},
    {"id": "party", "title": "Party", "url": "https://media.giphy.com/media/l3q2zVr6cu75FskyI/giphy.gif", "tags": "party celebrate"},
    {"id": "cry", "title": "Cry", "url": "https://media.giphy.com/media/ROF8OQvDymDlQfeBR5/giphy.gif", "tags": "cry sad"},
    {"id": "wow", "title": "Wow", "url": "https://media.giphy.com/media/3oEjI5VtIhHvK37WYo/giphy.gif", "tags": "wow surprise"},
    {"id": "ok", "title": "OK", "url": "https://media.giphy.com/media/xT9IgG50Fb7Mi0prBC/giphy.gif", "tags": "ok sure"},
    {"id": "thanks", "title": "Thanks", "url": "https://media.giphy.com/media/osjgQPWRx3mpc/giphy.gif", "tags": "thanks thank you"},
    {"id": "dance", "title": "Dance", "url": "https://media.giphy.com/media/BBt9eqHkZQRg2oHqF1/giphy.gif", "tags": "dance music"},
    {"id": "facepalm", "title": "Facepalm", "url": "https://media.giphy.com/media/XYly8aYpCqCOo/giphy.gif", "tags": "facepalm fail"},
    {"id": "hello", "title": "Hello", "url": "https://media.giphy.com/media/dzaUX7b0uD7kQ/giphy.gif", "tags": "hello hi wave"},
]

def _fetch_json(url, timeout=6):
    req = urllib.request.Request(url, headers={"User-Agent": "MezalionChat/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def _curated_gif_results(query=""):
    q = (query or "").strip().lower()
    items = CURATED_GIFS
    if q:
        items = [item for item in items if q in item["title"].lower() or q in item["tags"]]
    return [{"id": item["id"], "title": item["title"], "preview": item["url"], "url": item["url"]} for item in items]

@app.route("/api/gifs")
def api_gifs():
    user_id, response = require_user()
    if response:
        return response
    query = request.args.get("q", "").strip()
    giphy_key = os.environ.get("GIPHY_API_KEY", "").strip()
    if giphy_key:
        endpoint = "https://api.giphy.com/v1/gifs/search" if query else "https://api.giphy.com/v1/gifs/trending"
        params = {"api_key": giphy_key, "limit": "24", "rating": "pg-13"}
        if query:
            params["q"] = query
        try:
            data = _fetch_json(f"{endpoint}?{urllib.parse.urlencode(params)}")
            results = []
            for item in data.get("data", []):
                images = item.get("images") or {}
                preview = (images.get("fixed_width_small") or images.get("preview_gif") or {}).get("url")
                full = (images.get("downsized") or images.get("original") or {}).get("url")
                if preview and full:
                    results.append({
                        "id": item.get("id"),
                        "title": item.get("title") or "GIF",
                        "preview": preview,
                        "url": full,
                    })
            if results:
                return jsonify({"results": results, "source": "giphy"})
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
            pass

    tenor_key = os.environ.get("TENOR_API_KEY", "LIVDSRZULELA").strip()
    try:
        if query:
            url = "https://g.tenor.com/v1/search?" + urllib.parse.urlencode({
                "q": query, "key": tenor_key, "limit": 24, "media_filter": "minimal",
            })
        else:
            url = "https://g.tenor.com/v1/trending?" + urllib.parse.urlencode({
                "key": tenor_key, "limit": 24, "media_filter": "minimal",
            })
        data = _fetch_json(url)
        results = []
        for item in data.get("results", []):
            media = (item.get("media") or [{}])[0]
            gif = media.get("gif") or media.get("tinygif") or {}
            tiny = media.get("tinygif") or media.get("nanogif") or gif
            gif_url = gif.get("url")
            preview = tiny.get("url") or gif_url
            if gif_url:
                results.append({
                    "id": item.get("id"),
                    "title": item.get("content_description") or item.get("title") or "GIF",
                    "preview": preview,
                    "url": gif_url,
                })
        if results:
            return jsonify({"results": results, "source": "tenor"})
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError):
        pass

    return jsonify({"results": _curated_gif_results(query), "source": "curated"})

@app.route("/chat/notification-sound")
def chat_notification_sound():
    user_id, response = require_user()
    if response:
        return response
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        "0bf6b8800a2445bfaf9a69e941e92299_mixkit-interface-option-select-2573.wav",
        mimetype="audio/wav",
    )

@app.route("/chat/<int:conversation_id>/files/<int:item_id>/download")
def download_shared_file(conversation_id, item_id):
    user_id, response = require_user()
    if response:
        return response
    item = can_access_shared_item(item_id, user_id, conversation_id)
    if not item:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], item[3], as_attachment=True, download_name=item[2])

@app.route("/chat/<int:conversation_id>/files/<int:item_id>/preview")
def preview_shared_file(conversation_id, item_id):
    user_id, response = require_user()
    if response:
        return response
    item = can_access_shared_item(item_id, user_id, conversation_id)
    if not item:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], item[3], as_attachment=False, mimetype=item[4])

MAX_VOICE_BYTES = 10 * 1024 * 1024
ALLOWED_VOICE_MIME = {
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/aac",
    "audio/mp3",
}

@app.route("/chat/<int:conversation_id>/voice", methods=["POST"])
def upload_voice_message(conversation_id):
    user_id, response = require_user()
    if response:
        return response
    if not get_conversation(conversation_id, user_id):
        abort(404)
    file = request.files.get("audio")
    if not file:
        return jsonify({"error": "No audio received."}), 400
    mime_type = (file.mimetype or "").split(";")[0].strip().lower() or "audio/webm"
    if mime_type not in ALLOWED_VOICE_MIME and not mime_type.startswith("audio/"):
        return jsonify({"error": "Unsupported audio format."}), 400
    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)
    if size_bytes <= 0:
        return jsonify({"error": "Empty recording."}), 400
    if size_bytes > MAX_VOICE_BYTES:
        return jsonify({"error": "Voice message is too large (max 10 MB)."}), 413
    if get_storage_usage(user_id) + size_bytes > STORAGE_QUOTA:
        return jsonify({"error": "This upload exceeds your storage quota."}), 400
    ext = {
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/mp4": "m4a",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/aac": "aac",
    }.get(mime_type, "webm")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    short_id = uuid4().hex[:6]
    uploaded_name = secure_filename(file.filename or "") if file.filename else ""
    if uploaded_name and not uploaded_name.lower().startswith("voice-message"):
        base, uploaded_ext = os.path.splitext(uploaded_name)
        original_name = f"{base or 'voice'}-{short_id}{uploaded_ext or f'.{ext}'}"
    else:
        original_name = f"voice-{stamp}-{short_id}.{ext}"
    stored_name = f"{uuid4().hex}_{original_name}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], stored_name))
    item_id = add_storage_item(user_id, original_name, stored_name, mime_type, size_bytes)
    voice_folder_id = get_or_create_storage_folder(user_id, "Voice_messages")
    if voice_folder_id:
        move_storage_item(item_id, user_id, voice_folder_id)
    message_id = add_message(conversation_id, user_id, None, item_id)
    sender = get_user_by_id_safe(user_id)
    payload = {
        "id": message_id,
        "sender_id": user_id,
        "body": None,
        "storage_item_id": item_id,
        "filename": original_name,
        "mime_type": mime_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile_picture": sender[3] if sender else None,
    }
    socketio.emit("new_message", payload, room=f"conversation:{conversation_id}")
    return jsonify({"ok": True, "message": payload})

def sanitize_chat_body(body):
    if not body:
        return None
    body = body.strip()
    if not body:
        return None
    if body.startswith("gif:"):
        url = body[4:].strip()
        try:
            parsed = urllib.parse.urlparse(url)
        except ValueError:
            return None
        host = (parsed.hostname or "").lower()
        allowed = host.endswith("giphy.com") or host.endswith("tenor.com")
        if parsed.scheme != "https" or not allowed:
            return None
        return f"gif:{url}"
    if body.startswith("sticker:"):
        emoji = body[8:].strip()
        if not emoji or len(emoji) > 32:
            return None
        return f"sticker:{emoji}"
    return body[:4000]

@socketio.on("join_chat")
def join_chat(data):
    user_id = current_user_id()
    conversation_id = int(data.get("conversation_id", 0))
    if user_id and get_conversation(conversation_id, user_id):
        join_room(f"conversation:{conversation_id}")

@socketio.on("send_message")
def send_chat_message(data):
    user_id = current_user_id()
    conversation_id = int(data.get("conversation_id", 0))
    body = sanitize_chat_body((data.get("body") or "").strip() or None)
    storage_item_ids = data.get("storage_item_ids") or []
    single_id = data.get("storage_item_id")
    if single_id and single_id not in storage_item_ids:
        storage_item_ids = [single_id, *storage_item_ids]
    if not user_id or not get_conversation(conversation_id, user_id):
        return
    cleaned_ids = []
    for raw_id in storage_item_ids:
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        item = get_storage_item(item_id)
        if item and item[1] == user_id:
            cleaned_ids.append(item_id)
    if not body and not cleaned_ids:
        return
    sender = get_user_by_id_safe(user_id)
    if cleaned_ids:
        for index, item_id in enumerate(cleaned_ids):
            message_body = body if index == 0 else None
            message_id = add_message(conversation_id, user_id, message_body, item_id)
            attachment = get_storage_item(item_id)
            socketio.emit(
                "new_message",
                {
                    "id": message_id,
                    "sender_id": user_id,
                    "body": message_body,
                    "storage_item_id": item_id,
                    "filename": attachment[2] if attachment else None,
                    "mime_type": attachment[4] if attachment else None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "profile_picture": sender[3] if sender else None,
                },
                room=f"conversation:{conversation_id}",
            )
    else:
        message_id = add_message(conversation_id, user_id, body, None)
        socketio.emit(
            "new_message",
            {
                "id": message_id,
                "sender_id": user_id,
                "body": body,
                "storage_item_id": None,
                "filename": None,
                "mime_type": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "profile_picture": sender[3] if sender else None,
            },
            room=f"conversation:{conversation_id}",
        )

@app.route("/faqs")
def faqs_page():
    return render_template("faqs.html", intro_theme=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=port_number, debug=True)
    