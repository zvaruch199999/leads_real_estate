from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import sqlite3

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN"
ADMIN_GROUP_ID = -1001234567890

# ---------- DATABASE ----------
conn = sqlite3.connect(":memory:", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    status TEXT
)
""")
conn.commit()

# ---------- COMMANDS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute(
        "INSERT INTO requests (user_id, status) VALUES (?, ?)",
        (update.effective_user.id, "🟡 В пошуках")
    )
    conn.commit()
    req_id = cursor.lastrowid

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔵 В роботу", callback_data=f"status_work_{req_id}")],
        [InlineKeyboardButton("✅ Знайдено", callback_data=f"status_done_{req_id}")],
        [InlineKeyboardButton("❌ Неактуально", callback_data=f"status_cancel_{req_id}")]
    ])

    await update.message.reply_text(
        f"📋 Запит №{req_id}\n🔄 Статус: 🟡 В пошуках",
        reply_markup=keyboard
    )

    await context.bot.send_message(
        ADMIN_GROUP_ID,
        f"📥 Новий запит №{req_id}",
        reply_markup=keyboard
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute(
        "SELECT id, status FROM requests WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (update.effective_user.id,)
    )
    row = cursor.fetchone()

    if not row:
        await update.message.reply_text("❌ У вас немає активних запитів.")
        return

    await update.message.reply_text(
        f"📋 Запит №{row[0]}\n🔄 Статус: {row[1]}"
    )

# ---------- CALLBACK ----------

async def status_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    _, action, req_id = q.data.split("_")
    status_map = {
        "work": "🔵 Опрацьовується",
        "done": "✅ Житло знайдено",
        "cancel": "❌ Неактуально"
    }

    new_status = status_map[action]
    cursor.execute(
        "UPDATE requests SET status=? WHERE id=?",
        (new_status, int(req_id))
    )
    conn.commit()

    await q.message.edit_text(
        f"📋 Запит №{req_id}\n🔄 Статус: {new_status}"
    )

# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(status_update, pattern="^status_"))

    app.run_polling()

if __name__ == "__main__":
    main()
