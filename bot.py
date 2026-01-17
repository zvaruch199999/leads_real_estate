from telegram import *
from telegram.ext import *
import sqlite3
from datetime import datetime

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN"
ADMIN_GROUP_ID = -1001234567890

# ---------- DATABASE ----------

conn = sqlite3.connect("requests.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    phone TEXT,
    city TEXT,
    district TEXT,
    deal TEXT,
    property TEXT,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()

# ---------- HELPERS ----------

def save_request(u):
    cursor.execute("""
    INSERT INTO requests (user_id, name, phone, city, district, deal, property, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        u["user_id"], u["name"], u["phone"], u["city"],
        u["district"], u["deal"], u["property"],
        "🟡 В пошуках",
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    conn.commit()
    return cursor.lastrowid


def update_status(req_id, status):
    cursor.execute("UPDATE requests SET status=? WHERE id=?", (status, req_id))
    conn.commit()


def get_request_by_user(user_id):
    cursor.execute(
        "SELECT id, city, district, status FROM requests WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    return cursor.fetchone()

# ---------- START ----------

async def start(update: Update, ctx):
    await update.message.reply_text("👋 Вітаємо! Бот працює стабільно ✅")

# ---------- STATUS FOR CLIENT ----------

async def status_command(update: Update, ctx):
    row = get_request_by_user(update.message.from_user.id)

    if not row:
        await update.message.reply_text("❌ У вас немає активних запитів.")
        return

    req_id, city, district, status = row
    await update.message.reply_text(
        f"📋 Запит №{req_id}\n"
        f"📍 {city} / {district}\n\n"
        f"🔄 Статус: {status}"
    )

# ---------- STATUS FROM GROUP ----------

async def status_update_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    _, action, req_id = q.data.split("_")
    req_id = int(req_id)

    if action == "work":
        update_status(req_id, "🔵 Опрацьовується")
    elif action == "done":
        update_status(req_id, "✅ Житло знайдено")
    else:
        update_status(req_id, "❌ Неактуально")

    await q.message.reply_text("✅ Статус оновлено")

# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(status_update_handler, pattern="^status_"))

    app.run_polling()

if __name__ == "__main__":
    main()
