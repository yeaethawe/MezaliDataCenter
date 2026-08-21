from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory, abort, jsonify
from datetime import timedelta
import base64
import os
import socket
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, join_room
from database import (login_user, get_user_by_id, add_user, get_all_users, update_username,
                      delete_user, get_all_products, get_user_by_email, get_user_by_id_safe,
                      add_storage_item, get_storage_items, get_storage_usage, get_storage_item,
                      delete_storage_item, get_or_create_conversation, get_conversation,
                      get_messages, add_message, can_access_shared_item, search_users,
                      get_user_conversations, get_storage_items_in_folder, get_storage_folders,
                      add_storage_folder, get_storage_folder, rename_storage_item, move_storage_item,
                      update_user_name, change_user_password, update_profile_picture,
                      get_or_create_storage_folder, get_storage_folders_in_folder,
                      move_storage_folder, delete_storage_folder)
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
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
port_number = 80
STORAGE_QUOTA = 1024 * 1024 * 1024
MAX_UPLOAD_SIZE = 500 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "avi", "mkv", "webm",
    "mp3", "wav", "ogg", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "csv", "zip", "rar", "7z",
}

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
    return user_id, None

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def profile_picture_path(stored_name):
    return os.path.join(app.config["UPLOAD_FOLDER"], stored_name)

@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template("error.html", error="The server does not allow files larger than 500 MB."), 413

#print(f"the website is serving on http://{local_ip}:{port_number}")

# Define the route for the home/root URL
@app.route("/", methods=["GET", "POST"])
def main_route():
    return render_template("index.html")

#Define the root for viewing all users
@app.route("/users", methods=["GET", "POST"])
def users_route():
    if request.method == "POST":
        u_name = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        err = add_user(u_name, email, password)
        if err:
            return render_template("error.html", error=err)
        session["user_id"] = err if isinstance(err, int) else database.get_user_by_email(email)[0]
        session.pop("user", None)
        session.permanent = request.form.get("remember_me") == "on"
        return render_template("success.html", d1= "username : "+u_name, d2="email : "+email)
    return render_template("users.html", users = get_all_users())

@app.route('/users/<id>', methods=["GET", "POST"])
def user(id):
    return render_template("user.html", users=get_user_by_id(id))

@app.route("/userup", methods=["GET", "POST"])
def userup():
    if request.method == "POST":
        u_name = request.form.get("username")
        email = request.form.get("email")
        update_username(u_name, email)
        return render_template("success.html", d1="Username has changed successfully.", d2=u_name)

@app.route("/userdel", methods=["POST"])
def userdel():
    if request.method == "POST":
        email = request.form.get("email")
        delete_user(email)
        return render_template("success.html", d1= "The account is deleted with email: ", d2=email)
# Run the app automatically when executing the script

@app.route("/products", methods=["GET","POST"])
def products():
    if request.method == "POST":
        name = request.form.get("name")
        img = request.form.get("img")
        price = request.form.get("price")
        decryption = request.form.get("decryption")
        e = database.add_product(name, img, price, decryption)
        if e:
            return render_template("error.html", error=e)
        return render_template("success.html", d1="The product is added successfully.", d2=f"Product name is {name}")
    return render_template("products.html", products = get_all_products())

@app.route("/products/add", methods=["GET", "POST"])
def add_product():
    return render_template("addproduct.html")

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
    if request.method == "POST":
        email = request.form.get("email")
        e = database.delete_user(email)
        if e:
            return render_template("error.html", error=e)
        return render_template("success.html", d1="The user is successfully deleted.", d2=f"user email is {email}")
    return render_template("deluser.html")

@app.route("/register")
def register_user_page():
    if current_user_id():
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["POST", "GET"])
def login_user_page():
    if current_user_id():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        status = login_user(email, password)
        if status:
            session["user_id"] = status[0][0]
            session.pop("user", None)
            session.permanent = request.form.get("remember_me") == "on"
            return redirect(url_for("dashboard"))
        else:
            return render_template("error.html", error="User not found or incorrect password.")
            
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    user_id, response = require_user()
    if response:
        return response
    user = get_user_by_id_safe(user_id)
    return render_template("dashboard.html", user=user, storage_items=get_storage_items(user_id), storage_usage=get_storage_usage(user_id), storage_quota=STORAGE_QUOTA)

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
    if not filename or not allowed_file(filename):
        return render_template("error.html", error="That file type is not allowed."), 400
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
    item_id = add_storage_item(user_id, filename, stored_name, file.mimetype or "application/octet-stream", size_bytes)
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
    if not name or not allowed_file(name):
        return render_template("error.html", error="Enter a valid file name with an allowed extension."), 400
    stored_name = f"{uuid4().hex}_{name}"
    open(os.path.join(app.config["UPLOAD_FOLDER"], stored_name), "wb").close()
    item_id = add_storage_item(user_id, name, stored_name, "text/plain", 0)
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
    return redirect(url_for("file_explorer", folder_id=parent_id))

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
    if not item or item[1] != user_id or not item[4].startswith("text/"):
        abort(404)
    content = request.form.get("content", "")
    with open(os.path.join(app.config["UPLOAD_FOLDER"], item[3]), "w", encoding="utf-8") as file:
        file.write(content)
    return redirect(url_for("file_explorer", folder_id=request.form.get("folder_id", type=int)))

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
    )

@app.route("/chat/history/<int:conversation_id>")
def chat_history(conversation_id):
    user_id, response = require_user()
    if response:
        return response
    if not get_conversation(conversation_id, user_id):
        abort(404)
    return jsonify([{"id": row[0], "sender_id": row[1], "sender_name": row[2], "body": row[3], "storage_item_id": row[4], "filename": row[5], "mime_type": row[6], "created_at": row[7], "profile_picture": row[8]} for row in get_messages(conversation_id, user_id)])

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
    body = (data.get("body") or "").strip() or None
    storage_item_id = data.get("storage_item_id")
    if not user_id or not get_conversation(conversation_id, user_id):
        return
    if storage_item_id:
        item = get_storage_item(int(storage_item_id))
        if not item or item[1] != user_id:
            return
        storage_item_id = int(storage_item_id)
    if not body and not storage_item_id:
        return
    message_id = add_message(conversation_id, user_id, body, storage_item_id)
    attachment = get_storage_item(storage_item_id) if storage_item_id else None
    sender = get_user_by_id_safe(user_id)
    socketio.emit("new_message", {"id": message_id, "sender_id": user_id, "body": body, "storage_item_id": storage_item_id, "filename": attachment[2] if attachment else None, "mime_type": attachment[4] if attachment else None, "profile_picture": sender[3] if sender else None}, room=f"conversation:{conversation_id}")

@app.route("/faqs")
def faqs_page():
    return render_template("faqs.html")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=port_number, debug=True)
    