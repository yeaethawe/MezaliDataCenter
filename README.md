# 🦁 Mezalion

### Where your files roar, your chats sparkle, and your data gets a kingdom of its own.

Welcome to **Mezalion** — a colourful little digital citadel built with Flask. Think of it as a personal data-center that learned to dance: one place for **chat**, **files**, **profiles**, and **team control**, wrapped in a dark-mode-friendly shell that feels more *adventure* than *spreadsheet*.

---

## ✨ The legend (what this project is)

Once upon a localhost, someone wanted Telegram energy, a cloud drive, and an admin dashboard — **without** juggling five different apps.

So Mezalion was born:

| Realm | What happens there |
| --- | --- |
| 💬 **Chat** | Real-time private conversations with bubbles, stickers, GIFs, voice notes, search, and Telegram-style settings |
| 🗂️ **Storage & IDE** | Fold folders like treasure chests, upload files, browse, edit, share, and right-click like a power user |
| 👤 **Profiles & Dashboard** | Your face, your keys, your notifications — a home base for everyday ops |
| 🛡️ **Admin powers** | Users, products, locks, and host-side control when you hold the crown |

It’s not “just another CRUD demo.” It’s a **mini Mezalion universe**: collaborate, stash data, and keep the lights on — all in one Flask adventure.

---

## 🌈 Why it feels fantastical

- **Chat that behaves like a messenger**, not a form — live sockets, media panels, voice messages, and a settings labyrinth of themes, wallpapers, bubble colours, and interface scale  
- **Files with personality** — explorer + IDE vibes, public share links, and attachments that leap from storage straight into chat  
- **A branded intro** — Mezalion isn’t a grey template; it shows up with its own icon, wordmark, and night-sky dark theme  
- **Host-first energy** — your data lives on *your* stack (SQLite + uploads), so the kingdom stays yours  

---

## 🗺️ Map of the kingdom

```
flaskApp/
├── app.py              # Routes, sockets, and the main quest log
├── database.py         # The vault of users, chats, files, and lore
├── requirements.txt    # Potion ingredients (dependencies)
├── static/             # Themes, IDE CSS/JS, chat media magic
├── templates/          # Pages: chat, files, IDE, dashboard, profiles…
└── uploads/            # Treasure chests (gitignored — keep them secret)
```

---

## 🚀 Summon Mezalion locally

```bash
# 1. Enter the realm
cd flaskApp

# 2. (Optional but wise) create a virtual realm
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Drink the dependency potion
pip install -r requirements.txt

# 4. Awaken the server
python app.py
```

Then open your browser to the local URL printed in the terminal (usually `http://127.0.0.1:5000`) and **Get Started**.

---

## 🧩 Core spells (features)

- **Secure-ish social core** — register, login, profiles, password & picture settings  
- **Private chat** — Socket.IO realtime, attachments from storage, emoji/sticker/GIF panel, voice notes, edit/delete, in-chat search  
- **Chat settings** — themes, bubble shape/colour, wallpapers, sounds, dark mode, scale, and more  
- **File explorer / IDE** — folders, upload, preview, download, copy/move/delete, public share folders  
- **Dashboard & admin** — notifications, user management, products, admin-key upgrades  

---

## 🛠️ Built with

- **Python + Flask** — the castle walls  
- **Flask-SocketIO** — the messenger hawks (realtime chat)  
- **SQLite** — the pocket-sized vault  
- **Bootstrap + custom CSS/JS** — the colourful cloak  

---

## 📜 A friendly scroll of notes

- Keep `admin_keys.txt`, `.env`, and `uploads/` out of public commits (already ignored).  
- Large uploads and voice files live under `uploads/` — treat that folder like dragon gold.  
- Dark mode preference is remembered in the browser; chat cosmetics live in `localStorage`.  

---

## 🎉 Closing cheer

Mezalion is for builders who want a **fun, colourful, all-in-one** playground: chat like a messenger, file like a drive, manage like a host.

**Store your data. Spark your chats. Rule your little cloud.**  
Welcome to Mezalion. 🦁✨
